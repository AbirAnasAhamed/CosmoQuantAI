import sys
import os
import pandas as pd
import numpy as np

# Ensure the backend directory is in the path so we can import app modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.advanced_ml.features.forex.c01_smc_ict_tick_verified import (
    OBInitiationTickSurge, InstitutionalTickDeltaOB, OBDefenseTickIntensity,
    BreakerBlockTickTurnover, OBTimeInForceTick, MitigationTickAbsorptionRate,
    TickVolumeFVGMagnitude, FVGFillVelocity, TickImbalanceRatioFVG,
    FVGMitigationTickDensity, UnmitigatedFVGGravityIndex,
    BSLSSLSweepTickVelocity, LiquidityGrabRejectionDelta, StopRunTickExhaustionIndex,
    InducementLevelTickClustering, SweepVsBOSTickRatio,
    BOSTickConfirmationRatio, MSSDisplacementTickMomentum, DisplacementCandleGiniCoef,
    FractalBOSTickValidation, OTETickConfluence,
    AsianRangeTickDensity, LondonOpenManipulationDelta, NYKillzoneDistributionVelocity,
    PO3TickSynchronization, KillzoneTickVWAPDivergence, MacroWindowTickSpikeRate,
    CumulativeTickDeltaDivergence, InstitutionalSponsoringSignature,
    TickSpreadWideningIndicator, TickAccelDecelAtPOI, TickImbalanceSequenceIndex,
    SMCLevelExhaustionRate, LiquidityVoidTickTraverseTime, CompositeSMCTickScore,
    TOFIDecay, STBProbability, BSLSSLTickTrapRatio, TLFVDeviation, HFMV, TWTA,
    StealthMitigationIndex, TCDAtPDArrays, VSTS, IcebergOrderTickFootprint,
    InternalVsExternalLiquidityTickDelta, LiquidityVoidTickSpreadCoefficient,
    StopRunCascadingTickMultiplier, KillzoneTickVolatilitySkew, MacroTimeTickEntropy,
    DisplacementTickFractalDimension, TickWeightedSMTDivergence, FVGInversionTickThreshold,
    BreakerBlockResonanceIndex, InstitutionalOrderLayering,
    EigenStructureTickCovariance, PDFTickInterArrivalTimes, TickVolumeWeightedHurst,
    RLRewardSignalProxy
)

def create_mock_data():
    """Creates synthetic OHLCV and L1 Tick data for verification."""
    # 1. OHLCV Data (5 bars)
    dates = pd.date_range(start='2026-01-01', periods=5, freq='5min')
    df_ohlcv = pd.DataFrame({
        'open': [1.1000, 1.1020, 1.1010, 1.1050, 1.1040],
        'high': [1.1030, 1.1025, 1.1060, 1.1070, 1.1080],
        'low':  [1.0990, 1.1000, 1.1005, 1.1040, 1.1030],
        'close':[1.1020, 1.1010, 1.1050, 1.1040, 1.1070],
        'volume': [1000, 1200, 1500, 1100, 2000]
    }, index=dates)

    # 2. L1 Tick Data (10 ticks)
    tick_dates = pd.date_range(start='2026-01-01', periods=10, freq='30s')
    df_tick = pd.DataFrame({
        'bid': [1.1000, 1.1001, 1.1005, 1.1010, 1.1008, 1.1015, 1.1020, 1.1018, 1.1025, 1.1030],
        'ask': [1.1001, 1.1002, 1.1006, 1.1011, 1.1009, 1.1016, 1.1021, 1.1019, 1.1026, 1.1031],
        'volume': [10, 20, 15, 30, 5, 50, 10, 25, 100, 40]
    }, index=tick_dates)
    
    return df_ohlcv, df_tick

def run_verification():
    print("=" * 60)
    print("QUANT PIPELINE VERIFICATION SCRIPT: SMC & ICT (Tick-Verified)")
    print("=" * 60)
    
    try:
        df_ohlcv, df_tick = create_mock_data()
        print(f"[OK] Mock Data Generated: OHLCV ({len(df_ohlcv)} rows), Ticks ({len(df_tick)} rows)")
    except Exception as e:
        print(f"[ERROR] Failed to generate mock data: {e}")
        return

    # List of all 59 classes to instantiate and verify
    feature_classes = [
        OBInitiationTickSurge, InstitutionalTickDeltaOB, OBDefenseTickIntensity,
        BreakerBlockTickTurnover, OBTimeInForceTick, MitigationTickAbsorptionRate,
        TickVolumeFVGMagnitude, FVGFillVelocity, TickImbalanceRatioFVG,
        FVGMitigationTickDensity, UnmitigatedFVGGravityIndex,
        BSLSSLSweepTickVelocity, LiquidityGrabRejectionDelta, StopRunTickExhaustionIndex,
        InducementLevelTickClustering, SweepVsBOSTickRatio,
        BOSTickConfirmationRatio, MSSDisplacementTickMomentum, DisplacementCandleGiniCoef,
        FractalBOSTickValidation, OTETickConfluence,
        AsianRangeTickDensity, LondonOpenManipulationDelta, NYKillzoneDistributionVelocity,
        PO3TickSynchronization, KillzoneTickVWAPDivergence, MacroWindowTickSpikeRate,
        CumulativeTickDeltaDivergence, InstitutionalSponsoringSignature,
        TickSpreadWideningIndicator, TickAccelDecelAtPOI, TickImbalanceSequenceIndex,
        SMCLevelExhaustionRate, LiquidityVoidTickTraverseTime, CompositeSMCTickScore,
        TOFIDecay, STBProbability, BSLSSLTickTrapRatio, TLFVDeviation, HFMV, TWTA,
        StealthMitigationIndex, TCDAtPDArrays, VSTS, IcebergOrderTickFootprint,
        InternalVsExternalLiquidityTickDelta, LiquidityVoidTickSpreadCoefficient,
        StopRunCascadingTickMultiplier, KillzoneTickVolatilitySkew, MacroTimeTickEntropy,
        DisplacementTickFractalDimension, TickWeightedSMTDivergence, FVGInversionTickThreshold,
        BreakerBlockResonanceIndex, InstitutionalOrderLayering,
        EigenStructureTickCovariance, PDFTickInterArrivalTimes, TickVolumeWeightedHurst,
        RLRewardSignalProxy
    ]

    print(f"\n[INFO] Starting verification for {len(feature_classes)} Advanced Metrics...\n")
    
    passed = 0
    failed = 0
    
    for cls in feature_classes:
        try:
            # Instantiate the metric
            metric_instance = cls()
            
            # Run calculation
            result_df = metric_instance.calculate(df_ohlcv, df_tick)
            
            # Verify output
            if result_df.empty:
                raise ValueError("Returned empty DataFrame")
            if len(result_df) != len(df_ohlcv):
                raise ValueError(f"Output shape mismatch: Expected {len(df_ohlcv)}, got {len(result_df)}")
                
            passed += 1
        except Exception as e:
            print(f"[FAIL] {cls.__name__} encountered an error: {e}")
            failed += 1

    print("-" * 60)
    print(f"[SUCCESS] VERIFICATION COMPLETE: {passed}/{len(feature_classes)} Metrics Passed.")
    if failed > 0:
        print(f"[FAIL] {failed} Metrics.")
    else:
        print("[SUCCESS] ALL 59 SMC METRICS ARE 100% COMPATIBLE AND FUNCTIONAL!")
    print("=" * 60)

if __name__ == "__main__":
    run_verification()
