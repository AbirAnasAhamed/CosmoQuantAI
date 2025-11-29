
import React, { useState, useEffect, useRef } from 'react';
import { CloudLightning, Cpu, Server, Terminal, Play, Square, Activity, Database, Layers, Timer, Zap, ShieldCheck, Lock, UploadCloud, Download, CheckCircle2, ChevronDown } from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, AreaChart, Area } from 'recharts';
import { TradingBot } from '../types';

interface TrainingMetric {
  epoch: number;
  loss: number;
  valLoss: number;
  accuracy: number;
}

interface VertexForgeProps {
  bots: TradingBot[];
  onDeploy: (botId: string, modelVersion: string, computeNode: string) => void;
}

export const VertexForge: React.FC<VertexForgeProps> = ({ bots, onDeploy }) => {
  const [isConnected, setIsConnected] = useState(false);
  const [isTraining, setIsTraining] = useState(false);
  const [selectedGpu, setSelectedGpu] = useState('H100');
  const [metrics, setMetrics] = useState<TrainingMetric[]>([]);
  const [logs, setLogs] = useState<string[]>([]);
  const [progress, setProgress] = useState(0);
  const logsEndRef = useRef<HTMLDivElement>(null);

  // LINK: Target Bot State
  const [targetBotId, setTargetBotId] = useState<string>(bots[0]?.id || '');
  
  // LINK: Dataset from Data Nexus (Mocked for now)
  const [datasets] = useState([
      { id: 'ds-1', name: 'OMNI-5Y-TICK-DATA-V2.parquet', size: '4.2 GB', rows: '12.5M' },
      { id: 'ds-2', name: 'BINANCE-L2-ORDERBOOK-SNAPSHOT.csv', size: '12.8 GB', rows: '45.2M' },
      { id: 'ds-3', name: 'REDDIT-SENTIMENT-MATRIX.json', size: '1.1 GB', rows: '5.2M' }
  ]);
  const [selectedDatasetId, setSelectedDatasetId] = useState('ds-1');

  // Hyperparameters
  const [config, setConfig] = useState({
    epochs: 100,
    batchSize: 64,
    learningRate: 0.0003,
    optimizer: 'AdamW',
  });

  const hardwareOptions = [
    { id: 'H100', name: 'NVIDIA H100 (80GB)', cores: '14,592 CUDA', memory: '80GB HBM3', cost: '$4.20/hr' },
    { id: 'A100', name: 'NVIDIA A100 (40GB)', cores: '6,912 CUDA', memory: '40GB HBM2', cost: '$2.90/hr' },
    { id: 'T4', name: 'NVIDIA T4', cores: '2,560 CUDA', memory: '16GB GDDR6', cost: '$0.35/hr' },
    { id: 'TPU', name: 'Google Cloud TPU v5p', cores: 'TensorCore Matrix', memory: '96GB HBM', cost: '$3.50/hr' },
  ];

  // Auto-scroll logs
  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  // Connect Simulation
  const handleConnect = () => {
    setLogs(prev => [...prev, "> Initializing secure handshake with Google Cloud Platform..."]);
    setTimeout(() => setLogs(prev => [...prev, "> Authenticating Service Account: omni-core-admin@vertex-ai.iam.gserviceaccount.com..."]), 800);
    setTimeout(() => {
        setIsConnected(true);
        setLogs(prev => [...prev, "> CONNECTION ESTABLISHED. Vertex AI Pipelines Ready."]);
    }, 2000);
  };

  // Training Loop Simulation
  useEffect(() => {
    if (!isTraining) return;

    let currentEpoch = metrics.length;
    let currentLoss = metrics.length > 0 ? metrics[metrics.length-1].loss : 0.8;
    
    const interval = setInterval(() => {
      if (currentEpoch >= config.epochs) {
        setIsTraining(false);
        const finalVersion = `v${Math.floor(Math.random()*10)}.${Math.floor(Math.random()*10)}-cuda-opt`;
        setLogs(prev => [...prev, `> TRAINING COMPLETE. Model saved: ${finalVersion}`]);
        return;
      }

      currentEpoch++;
      
      // Simulate Loss Reduction
      const noise = (Math.random() - 0.5) * 0.05;
      currentLoss = Math.max(0.01, currentLoss * 0.95 + noise);
      const valLoss = currentLoss * (1.05 + Math.random() * 0.05);
      const accuracy = Math.min(0.99, 1 - currentLoss);

      const newMetric: TrainingMetric = {
        epoch: currentEpoch,
        loss: parseFloat(currentLoss.toFixed(4)),
        valLoss: parseFloat(valLoss.toFixed(4)),
        accuracy: parseFloat((accuracy * 100).toFixed(2))
      };

      setMetrics(prev => [...prev.slice(-49), newMetric]);
      setProgress((currentEpoch / config.epochs) * 100);
      
      // Random Log Generation
      if (Math.random() > 0.6) {
          setLogs(prev => [...prev, `[EPOCH ${currentEpoch}/${config.epochs}] batch_loss=${currentLoss.toFixed(4)} | gpu_temp=${Math.floor(65 + Math.random()*10)}°C | vram_util=92%`]);
      }
    }, 500); // Speed of simulation

    return () => clearInterval(interval);
  }, [isTraining, config.epochs]);

  const startTraining = () => {
      setMetrics([]);
      const target = bots.find(b => b.id === targetBotId)?.name || 'Unknown Unit';
      const dsName = datasets.find(d => d.id === selectedDatasetId)?.name || 'Unknown Dataset';
      
      setLogs(prev => [
          `> TARGET UNIT: ${target}`,
          `> ALLOCATING RESOURCE: ${hardwareOptions.find(h => h.id === selectedGpu)?.name}`,
          `> MOUNTING DATASET: gs://omni-data/${dsName}`,
          `> COMPILING MODEL GRAPH (PyTorch 2.1 + CUDA 12.1)...`,
          `> INITIALIZING WEIGHTS (Xavier Uniform)...`,
          `> TRAINING STARTED.`
      ]);
      setIsTraining(true);
  };

  const stopTraining = () => {
      setIsTraining(false);
      setLogs(prev => [...prev, `> INTERRUPT SIGNAL RECEIVED. Halting CUDA streams...`]);
  };

  const deployModel = () => {
     const version = `v4.${Math.floor(Math.random()*9)}.${Math.floor(Math.random()*9)}-vertex`;
     const node = hardwareOptions.find(h => h.id === selectedGpu)?.name || 'Unknown Node';
     
     setLogs(prev => [...prev, `> DEPLOYING ${version} TO ${bots.find(b => b.id === targetBotId)?.name}...`]);
     
     setTimeout(() => {
         onDeploy(targetBotId, version, node);
         setLogs(prev => [...prev, `> DEPLOYMENT SUCCESSFUL. Bot updated.`]);
     }, 1000);
  };

  return (
    <div className="space-y-6 h-full flex flex-col">
      {/* Header */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 bg-omni-panel border border-slate-700 rounded-xl p-6 relative overflow-hidden">
         {/* Background Decoration */}
         <div className="absolute top-0 right-0 w-64 h-full bg-gradient-to-l from-blue-600/10 to-transparent pointer-events-none"></div>
         
         <div className="flex items-center gap-4 relative z-10">
             <div className="w-12 h-12 bg-blue-500/10 border border-blue-500/30 rounded-xl flex items-center justify-center">
                 <CloudLightning size={24} className="text-blue-400" />
             </div>
             <div>
                 <h2 className="text-2xl font-black text-white tracking-tight flex items-center gap-2">
                     VERTEX AI NEURAL FORGE
                     {isConnected && <span className="text-[10px] bg-green-500/20 text-green-400 px-2 py-0.5 rounded border border-green-500/30 font-mono">CONNECTED</span>}
                 </h2>
                 <p className="text-slate-400 text-sm font-mono">Google Cloud Platform // Custom Training Pipelines</p>
             </div>
         </div>

         {!isConnected ? (
             <button 
                onClick={handleConnect}
                className="px-6 py-3 bg-blue-600 hover:bg-blue-500 text-white font-bold rounded-lg flex items-center gap-2 shadow-lg shadow-blue-900/20 transition-all"
             >
                 <UploadCloud size={20} /> INITIALIZE GCP LINK
             </button>
         ) : (
             <div className="flex items-center gap-4 text-xs font-mono">
                 <div className="flex items-center gap-2 px-3 py-1.5 bg-slate-800 rounded border border-slate-700 text-slate-300">
                     <ShieldCheck size={14} className="text-green-400" /> IAM: ROOT_ADMIN
                 </div>
                 <div className="flex items-center gap-2 px-3 py-1.5 bg-slate-800 rounded border border-slate-700 text-slate-300">
                     <Database size={14} className="text-blue-400" /> Region: us-central1-a
                 </div>
             </div>
         )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 flex-1 min-h-0">
          
          {/* LEFT: Configuration */}
          <div className="lg:col-span-3 space-y-6 overflow-y-auto pr-2">
              
              {/* TARGET BOT SELECTOR (THE LINK) */}
              <div className="bg-omni-panel border border-slate-700 rounded-xl p-5">
                  <h3 className="text-sm font-bold text-white mb-4 flex items-center gap-2">
                      <Zap size={16} className="text-yellow-400" /> Target Neural Unit
                  </h3>
                  <div className="relative">
                      <select 
                          value={targetBotId}
                          onChange={(e) => setTargetBotId(e.target.value)}
                          className="w-full bg-slate-900 border border-slate-700 rounded-lg p-3 text-white appearance-none focus:border-yellow-500 outline-none text-sm font-bold"
                          disabled={isTraining}
                      >
                          {bots.map(bot => (
                              <option key={bot.id} value={bot.id}>
                                  {bot.name} [{bot.strategy}]
                              </option>
                          ))}
                      </select>
                      <ChevronDown className="absolute right-3 top-3 text-slate-400 pointer-events-none" size={16} />
                  </div>
                  <div className="mt-2 text-xs text-slate-500">
                      Current Model: <span className="text-slate-300 font-mono">{bots.find(b => b.id === targetBotId)?.modelVersion || 'v0.0.0-init'}</span>
                  </div>
              </div>

              {/* DATASET SELECTOR (LINK TO NEXUS) */}
              <div className="bg-omni-panel border border-slate-700 rounded-xl p-5">
                   <h3 className="text-sm font-bold text-white mb-4 flex items-center gap-2">
                       <Database size={16} className="text-blue-400" /> Training Data (Nexus)
                   </h3>
                   <div className="space-y-3">
                       {datasets.map(ds => (
                           <div 
                               key={ds.id}
                               onClick={() => !isTraining && setSelectedDatasetId(ds.id)}
                               className={`p-3 rounded-lg border cursor-pointer transition-all ${
                                   selectedDatasetId === ds.id 
                                   ? 'bg-blue-500/10 border-blue-500' 
                                   : 'bg-slate-800/50 border-slate-700 hover:border-slate-600'
                               }`}
                           >
                               <div className="flex justify-between items-center">
                                   <div className="text-xs font-bold text-slate-300 truncate max-w-[150px]">{ds.name}</div>
                                   {selectedDatasetId === ds.id && <div className="w-2 h-2 rounded-full bg-blue-500"></div>}
                               </div>
                               <div className="flex justify-between mt-1 text-[10px] text-slate-500">
                                   <span>{ds.size}</span>
                                   <span>{ds.rows} Rows</span>
                               </div>
                           </div>
                       ))}
                   </div>
              </div>

              {/* Hardware Selector */}
              <div className="bg-omni-panel border border-slate-700 rounded-xl p-5">
                  <h3 className="text-sm font-bold text-white mb-4 flex items-center gap-2">
                      <Cpu size={16} className="text-omni-accent" /> Compute Cluster
                  </h3>
                  <div className="space-y-3">
                      {hardwareOptions.map((hw) => (
                          <div 
                             key={hw.id}
                             onClick={() => !isTraining && setSelectedGpu(hw.id)}
                             className={`p-3 rounded-lg border cursor-pointer transition-all ${
                                 selectedGpu === hw.id 
                                 ? 'bg-blue-500/10 border-blue-500 shadow-[0_0_10px_rgba(59,130,246,0.2)]' 
                                 : 'bg-slate-800/50 border-slate-700 hover:border-slate-500'
                             }`}
                          >
                              <div className="flex justify-between items-center mb-1">
                                  <span className={`font-bold text-sm ${selectedGpu === hw.id ? 'text-white' : 'text-slate-300'}`}>{hw.name}</span>
                                  <span className="text-xs font-mono text-slate-500">{hw.cost}</span>
                              </div>
                              <div className="flex justify-between items-center text-[10px] text-slate-400 font-mono">
                                  <span>{hw.cores}</span>
                                  <span>{hw.memory}</span>
                              </div>
                          </div>
                      ))}
                  </div>
              </div>

              {/* Hyperparameters */}
              <div className="bg-omni-panel border border-slate-700 rounded-xl p-5">
                  <h3 className="text-sm font-bold text-white mb-4 flex items-center gap-2">
                      <SettingsIcon size={16} className="text-purple-400" /> Hyperparameters
                  </h3>
                  <div className="space-y-4">
                      <div>
                          <label className="text-xs text-slate-400 block mb-1">Target Epochs</label>
                          <input 
                              type="number" 
                              value={config.epochs}
                              onChange={(e) => setConfig({...config, epochs: parseInt(e.target.value)})}
                              className="w-full bg-slate-900 border border-slate-700 rounded p-2 text-white font-mono text-sm"
                              disabled={isTraining}
                          />
                      </div>
                  </div>
              </div>
          </div>

          {/* MIDDLE: Visualization */}
          <div className="lg:col-span-6 flex flex-col gap-6 min-h-0">
              {/* Main Chart */}
              <div className="flex-1 bg-omni-panel border border-slate-700 rounded-xl p-4 flex flex-col min-h-[300px]">
                  <div className="flex justify-between items-center mb-4">
                      <h3 className="text-sm font-bold text-white flex items-center gap-2">
                          <Activity size={16} className="text-omni-accent" /> Training Convergence
                      </h3>
                      <div className="flex gap-4 text-xs font-mono">
                          <span className="flex items-center gap-1 text-omni-accent"><div className="w-2 h-2 rounded-full bg-omni-accent"></div> Loss</span>
                          <span className="flex items-center gap-1 text-purple-400"><div className="w-2 h-2 rounded-full bg-purple-400"></div> Val Loss</span>
                      </div>
                  </div>
                  <div className="flex-1 w-full min-h-0">
                      <ResponsiveContainer width="100%" height="100%">
                          <LineChart data={metrics}>
                              <CartesianGrid strokeDasharray="3 3" stroke="#334155" opacity={0.5} />
                              <XAxis dataKey="epoch" stroke="#64748b" tick={{fontSize: 10}} />
                              <YAxis stroke="#64748b" tick={{fontSize: 10}} domain={[0, 'auto']} />
                              <Tooltip contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #475569' }} />
                              <Line type="monotone" dataKey="loss" stroke="#38bdf8" strokeWidth={2} dot={false} isAnimationActive={false} />
                              <Line type="monotone" dataKey="valLoss" stroke="#a855f7" strokeWidth={2} dot={false} isAnimationActive={false} />
                          </LineChart>
                      </ResponsiveContainer>
                  </div>
              </div>

              {/* Accuracy Chart & Stats */}
              <div className="h-48 grid grid-cols-3 gap-4">
                   <div className="col-span-2 bg-omni-panel border border-slate-700 rounded-xl p-4 flex flex-col">
                        <h3 className="text-xs font-bold text-slate-400 mb-2">Model Accuracy</h3>
                        <div className="flex-1 min-h-0">
                             <ResponsiveContainer width="100%" height="100%">
                                <AreaChart data={metrics}>
                                    <defs>
                                        <linearGradient id="colorAcc" x1="0" y1="0" x2="0" y2="1">
                                            <stop offset="5%" stopColor="#10b981" stopOpacity={0.3}/>
                                            <stop offset="95%" stopColor="#10b981" stopOpacity={0}/>
                                        </linearGradient>
                                    </defs>
                                    <Area type="monotone" dataKey="accuracy" stroke="#10b981" fill="url(#colorAcc)" strokeWidth={2} isAnimationActive={false} />
                                </AreaChart>
                             </ResponsiveContainer>
                        </div>
                   </div>
                   <div className="col-span-1 bg-omni-panel border border-slate-700 rounded-xl p-4 flex flex-col justify-center gap-2">
                        <div className="text-center">
                            <div className="text-xs text-slate-500">Current Epoch</div>
                            <div className="text-2xl font-mono font-bold text-white">
                                {metrics.length > 0 ? metrics[metrics.length-1].epoch : 0}<span className="text-slate-600 text-sm">/{config.epochs}</span>
                            </div>
                        </div>
                        <div className="h-px bg-slate-700 w-full my-1"></div>
                        <div className="text-center">
                             <div className="text-xs text-slate-500">Est. Cost</div>
                             <div className="text-lg font-mono font-bold text-green-400">
                                 ${(metrics.length * 0.05).toFixed(2)}
                             </div>
                        </div>
                   </div>
              </div>
          </div>

          {/* RIGHT: Terminal & Control */}
          <div className="lg:col-span-3 flex flex-col gap-6 h-full min-h-0">
               {/* Terminal */}
               <div className="flex-1 bg-black border border-slate-700 rounded-xl p-4 font-mono text-xs overflow-hidden flex flex-col shadow-inner shadow-black/50">
                    <div className="flex justify-between items-center mb-2 border-b border-slate-800 pb-2">
                         <span className="text-slate-400 font-bold flex items-center gap-2"><Terminal size={12} /> TERMINAL_OUT</span>
                         <span className="animate-pulse text-green-500">● LIVE</span>
                    </div>
                    <div className="flex-1 overflow-y-auto scrollbar-thin scrollbar-thumb-slate-800 space-y-1">
                        {logs.length === 0 && <span className="text-slate-600 italic">System ready. Awaiting training command...</span>}
                        {logs.map((log, i) => (
                            <div key={i} className="text-slate-300 break-all border-l-2 border-transparent hover:border-slate-700 pl-1">
                                {log}
                            </div>
                        ))}
                        <div ref={logsEndRef} />
                    </div>
               </div>

               {/* Control Actions */}
               <div className="bg-omni-panel border border-slate-700 rounded-xl p-5">
                   {isTraining ? (
                       <div className="space-y-4">
                           <div className="w-full bg-slate-800 h-2 rounded-full overflow-hidden">
                               <div className="h-full bg-blue-500 transition-all duration-500" style={{width: `${progress}%`}}></div>
                           </div>
                           <button 
                               onClick={stopTraining}
                               className="w-full py-4 bg-red-600 hover:bg-red-500 text-white font-bold rounded-lg flex items-center justify-center gap-2 shadow-lg shadow-red-900/20"
                           >
                               <Square size={20} fill="currentColor" /> ABORT TRAINING
                           </button>
                       </div>
                   ) : (
                       <button 
                           onClick={startTraining}
                           disabled={!isConnected}
                           className={`w-full py-4 font-bold rounded-lg flex items-center justify-center gap-2 shadow-lg transition-all ${
                               isConnected 
                               ? 'bg-omni-success hover:bg-green-600 text-white shadow-green-900/20' 
                               : 'bg-slate-700 text-slate-500 cursor-not-allowed'
                           }`}
                       >
                           <Play size={20} fill="currentColor" /> START TRAINING RUN
                       </button>
                   )}

                   {/* Deploy Button (Only if metrics exist) */}
                   {metrics.length > 0 && !isTraining && (
                       <button 
                           onClick={deployModel}
                           className="w-full mt-3 py-3 border border-blue-500/30 bg-blue-500/10 text-blue-400 hover:bg-blue-500 hover:text-white font-bold rounded-lg flex items-center justify-center gap-2 transition-all"
                       >
                           <Download size={18} /> DEPLOY TO BOT FLEET
                       </button>
                   )}
               </div>
          </div>
      </div>
    </div>
  );
};

// Helper Icon
const SettingsIcon = ({ size, className }: any) => (
  <svg xmlns="http://www.w3.org/2000/svg" width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}><path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.47a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"></path><circle cx="12" cy="12" r="3"></circle></svg>
);
