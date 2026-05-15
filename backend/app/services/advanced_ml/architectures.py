import torch
import torch.nn as nn
import math
from stable_baselines3.common.torch_layers import BaseFeaturesExtractor
import gymnasium as gym

class PositionalEncoding(nn.Module):
    """Injects some information about the relative or absolute position of the tokens in the sequence."""
    def __init__(self, d_model: int, max_len: int = 5000):
        super(PositionalEncoding, self).__init__()
        pe = torch.zeros(max_len, d_model)
        position = torch.arange(0, max_len, dtype=torch.float).unsqueeze(1)
        div_term = torch.exp(torch.arange(0, d_model, 2).float() * (-math.log(10000.0) / d_model))
        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term)
        pe = pe.unsqueeze(0)
        self.register_buffer('pe', pe)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return x + self.pe[:, :x.size(1)]

class TimeSeriesTransformer(nn.Module):
    """
    A professional-grade Transformer for time-series prediction (OHLCV/L2).
    Includes Positional Encoding and multi-layer Encoder.
    """
    def __init__(
        self, 
        input_dim: int, 
        d_model: int = 64, 
        nhead: int = 4, 
        num_layers: int = 3, 
        dim_feedforward: int = 256,
        dropout: float = 0.1,
        output_dim: int = 1
    ):
        super(TimeSeriesTransformer, self).__init__()
        self.d_model = d_model
        
        # Input Projection: Projects features to d_model space
        self.input_proj = nn.Linear(input_dim, d_model)
        self.pos_encoder = PositionalEncoding(d_model)
        
        # Transformer Encoder
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model, 
            nhead=nhead, 
            dim_feedforward=dim_feedforward, 
            dropout=dropout,
            batch_first=True
        )
        self.transformer_encoder = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)
        
        # Output Head
        self.output_head = nn.Linear(d_model, output_dim)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Args:
            x: Input tensor of shape (Batch, Seq_Len, Features)
        Returns:
            Prediction for the next step.
        """
        # 1. Project and scale
        x = self.input_proj(x) * math.sqrt(self.d_model)
        
        # 2. Add Positional Encoding
        x = self.pos_encoder(x)
        
        # 3. Pass through Transformer Encoder
        # Output shape: (Batch, Seq_Len, d_model)
        x = self.transformer_encoder(x)
        
        # 4. Global average pooling or take the last token
        # Taking the last token's representation for the final decision
        x = x[:, -1, :]
        
        # 5. Final prediction
        return self.output_head(x)

class TransformerRLFeatureExtractor(BaseFeaturesExtractor):
    """
    Custom Feature Extractor for Stable-Baselines3 PPO.
    Wraps a Transformer to process sequential observations.
    
    Note: Requires the environment observation to be in shape (Seq_Len * Features) 
    or handles the reshaping internally.
    """
    def __init__(
        self, 
        observation_space: gym.Space, 
        features_dim: int = 128,
        seq_len: int = 60,
        d_model: int = 64
    ):
        super(TransformerRLFeatureExtractor, self).__init__(observation_space, features_dim)
        
        # Calculate input_dim (features per step)
        # Assumes observation is a flattened window of (seq_len, features)
        self.seq_len = seq_len
        self.features_per_step = observation_space.shape[0] // seq_len
        
        self.transformer = TimeSeriesTransformer(
            input_dim=self.features_per_step,
            d_model=d_model,
            nhead=4,
            num_layers=2,
            output_dim=features_dim # The output dimension for SB3
        )

    def forward(self, observations: torch.Tensor) -> torch.Tensor:
        # 1. Reshape flattened observation to (Batch, Seq_Len, Features)
        batch_size = observations.size(0)
        x = observations.view(batch_size, self.seq_len, self.features_per_step)
        
        # 2. Extract features using the Transformer
        return self.transformer(x)

# ── TCN (Temporal Convolutional Network) ────────────────────────────────────

class Chomp1d(nn.Module):
    def __init__(self, chomp_size):
        super(Chomp1d, self).__init__()
        self.chomp_size = chomp_size

    def forward(self, x):
        return x[:, :, :-self.chomp_size].contiguous()

class TemporalBlock(nn.Module):
    def __init__(self, n_inputs, n_outputs, kernel_size, stride, dilation, padding, dropout=0.2):
        super(TemporalBlock, self).__init__()
        self.conv1 = nn.Conv1d(n_inputs, n_outputs, kernel_size,
                               stride=stride, padding=padding, dilation=dilation)
        self.chomp1 = Chomp1d(padding)
        self.relu1 = nn.ReLU()
        self.dropout1 = nn.Dropout(dropout)

        self.conv2 = nn.Conv1d(n_outputs, n_outputs, kernel_size,
                               stride=stride, padding=padding, dilation=dilation)
        self.chomp2 = Chomp1d(padding)
        self.relu2 = nn.ReLU()
        self.dropout2 = nn.Dropout(dropout)

        self.net = nn.Sequential(self.conv1, self.chomp1, self.relu1, self.dropout1,
                                 self.conv2, self.chomp2, self.relu2, self.dropout2)
        self.downsample = nn.Conv1d(n_inputs, n_outputs, 1) if n_inputs != n_outputs else None
        self.relu = nn.ReLU()

    def forward(self, x):
        out = self.net(x)
        res = x if self.downsample is None else self.downsample(x)
        return self.relu(out + res)

class TCNModel(nn.Module):
    def __init__(self, input_size, num_channels, output_size=1, kernel_size=2, dropout=0.2):
        super(TCNModel, self).__init__()
        layers = []
        num_levels = len(num_channels)
        for i in range(num_levels):
            dilation_size = 2 ** i
            in_channels = input_size if i == 0 else num_channels[i-1]
            out_channels = num_channels[i]
            layers += [TemporalBlock(in_channels, out_channels, kernel_size, stride=1, dilation=dilation_size,
                                     padding=(kernel_size-1) * dilation_size, dropout=dropout)]
        self.network = nn.Sequential(*layers)
        self.linear = nn.Linear(num_channels[-1], output_size)

    def forward(self, x):
        # x is (Batch, Seq_Len, Features). Conv1d expects (Batch, Channels, Seq_Len)
        x = x.transpose(1, 2)
        y1 = self.network(x)
        return self.linear(y1[:, :, -1])

# ── TabNet (Custom PyTorch Implementation) ──────────────────────────────────

class TabNetEncoder(nn.Module):
    """Simplified Attentive Tabular Transformer for structured tabular data."""
    def __init__(self, input_dim, output_dim=1, n_steps=3, n_d=16, n_a=16):
        super(TabNetEncoder, self).__init__()
        self.n_steps = n_steps
        self.n_d = n_d
        self.n_a = n_a
        
        self.initial_bn = nn.BatchNorm1d(input_dim)
        
        # Feature Transformer (Simplified as MLP)
        self.feature_transform = nn.Sequential(
            nn.Linear(input_dim, (n_d + n_a) * 2),
            nn.BatchNorm1d((n_d + n_a) * 2),
            nn.ReLU(),
            nn.Linear((n_d + n_a) * 2, n_d + n_a)
        )
        
        # Attentive Transformer
        self.attentive_transform = nn.Sequential(
            nn.Linear(n_a, input_dim),
            nn.BatchNorm1d(input_dim)
        )
        
        self.final_mapping = nn.Linear(n_d, output_dim)

    def forward(self, x):
        # x shape (Batch, Features)
        x = self.initial_bn(x)
        prior = torch.ones_like(x)
        
        out = torch.zeros(x.size(0), self.n_d, device=x.device)
        a = torch.zeros(x.size(0), self.n_a, device=x.device)
        
        for step in range(self.n_steps):
            # Attentive Transformer
            mask = self.attentive_transform(a)
            # Sparsemax approximation using Softmax
            mask = torch.softmax(mask * prior, dim=1)
            prior = prior * (1.001 - mask)  # Update prior
            
            # Feature Transformer
            masked_x = mask * x
            ft_out = self.feature_transform(masked_x)
            
            d = ft_out[:, :self.n_d]
            a = ft_out[:, self.n_d:]
            
            out = out + torch.relu(d)
            
        return self.final_mapping(out)

# ── Auto-Encoder (Anomaly Detection) ────────────────────────────────────────

class AutoEncoder(nn.Module):
    """Unsupervised Auto-Encoder for Market Anomaly (Crash/Pump) Detection."""
    def __init__(self, input_dim, hidden_dim=32):
        super(AutoEncoder, self).__init__()
        
        self.encoder = nn.Sequential(
            nn.Linear(input_dim, hidden_dim * 2),
            nn.ReLU(),
            nn.Linear(hidden_dim * 2, hidden_dim),
            nn.ReLU()
        )
        
        self.decoder = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim * 2),
            nn.ReLU(),
            nn.Linear(hidden_dim * 2, input_dim)
        )

    def forward(self, x):
        encoded = self.encoder(x)
        decoded = self.decoder(encoded)
        return decoded

