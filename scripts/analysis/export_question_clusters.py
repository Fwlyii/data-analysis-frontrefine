"""Persist anonymous question-cluster ordering used by paired statistics."""
from pathlib import Path
import importlib.util
ROOT=next(p for p in Path(__file__).resolve().parents if (p/'project.json').is_file())
spec=importlib.util.spec_from_file_location('baseline_reproduction',ROOT/'scripts/reproduce_baselines.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);module.build_question_order()
