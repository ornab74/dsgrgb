# DysonSphereGamma RGB Rainbow Turnout Research Project

This archive packages the RGB/Gamma/Sync simulator, Rainbow Spectrum information projection, research paper, figures, exact terminal transcript, extracted outputs, and a turnout-only prediction prompt.

## Quick start

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
python -m pip install -r requirements.txt
cp .env.example .env
export OPENAI_API_KEY="your-key"
python main.py
```

Or run:

```bash
./run.sh
```

## Main files

- `main.py` — runnable v14 simulator.
- `requirements.txt` — runtime and paper-building dependencies.
- `.env.example` — environment-variable template with no credentials.
- `prompts/turnout_only_prediction_prompt.txt` — strict turnout-only synthetic prompt.
- `paper/RGB_Rainbow_Quantum_Simulation_Information_Theory_Research_Paper.docx` — complete DOCX research paper.
- `paper/build_paper.py` — portable paper-generation script.
- `paper/figures/` — ten original paper figures.
- `outputs/full_terminal_transcript.txt` — complete supplied terminal output.
- `outputs/turnout_loop_observer_outputs.txt` — extracted five-loop observer output.
- `outputs/final_risk_orchestrator_output.txt` — extracted final adjudicator output.
- `outputs/fusion_state.json` — extracted initial RGB/Rainbow fusion state.
- `outputs/turnout_consensus.json` — machine-readable synthetic turnout consensus.
- `outputs/turnout_consensus.txt` — readable synthetic turnout consensus.
- `MANIFEST.sha256` — integrity hashes for packaged files.

## Rebuild the paper

```bash
source .venv/bin/activate
python paper/build_paper.py
```

## Output provenance

The election-turnout numbers in this project are labeled `SYNTHETIC`. They are outputs of the simulator and prompt pipeline, not observed polling, official election data, or an empirically calibrated forecast.
