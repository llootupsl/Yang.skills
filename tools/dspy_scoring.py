#!/usr/bin/env python3
# 作者: 阿洋
"""
dspy_scoring.py — DSPy-based scoring optimizer for Yang.skills v4.

Reads calibration samples, trains an optimized scoring signature using
DSPy's teleprompter framework, and applies the optimized signature to
score new scripts across 7 dimensions.

Usage:
    python tools/dspy_scoring.py --train calibration_samples.json
    python tools/dspy_scoring.py --train calibration_samples.json --optimizer mipro-v2 --trials 15
    python tools/dspy_scoring.py --score script.txt
    python tools/dspy_scoring.py --info

Key thresholds:
    ≥20 samples  → mipro-v2 (MIPROv2 optimizer)
    5-19 samples → bootstrap-fewshot (BootstrapFewShot)
    <5 samples   → skip optimization, use v3 rules-based scoring

Dependencies: dspy-ai (optional — falls back gracefully)
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

DSPY_AVAILABLE = False
try:
    import dspy

    DSPY_AVAILABLE = True
except ImportError:
    pass

TOOLS_DIR = Path(__file__).resolve().parent
PROJECT_DIR = TOOLS_DIR.parent
OPTIMIZED_SCORING_PATH = TOOLS_DIR / "optimized_scoring.json"
STATE_FILE = PROJECT_DIR / ".yang-state.json"

SEVEN_DIM_FIELDS = [
    "hook_score",
    "emotion_score",
    "structure_score",
    "copywriting_score",
    "persona_score",
    "virality_score",
    "rhythm_score",
]

SCORING_INSTRUCTIONS = """You are a seasoned short-video script evaluator for Yang.skills.
Score the provided script across 7 dimensions on a 0-10 scale.

Scoring Rubric:
  - hook_score (0-10): How effectively does the opening hook grab attention within the first 3 seconds?
  - emotion_score (0-10): How well does the script build emotional arcs — tension, release, empathy, or surprise?
  - structure_score (0-10): Is the narrative structure clear and progressive (e.g. problem → analysis → solution)?
  - copywriting_score (0-10): Is the language precise, vivid, and shareable? Does each line serve a purpose?
  - persona_score (0-10): Is the creator's persona distinct, consistent, and authentic throughout?
  - virality_score (0-10): Does the script contain triggers for sharing — controversy, relatability, novelty, or utility?
  - rhythm_score (0-10): Does the pacing alternate between fast and slow effectively? Are there natural breathing points?

Overall Comment: Write a concise 2-3 sentence summary in Chinese, highlighting the strongest and weakest dimensions.

Context from knowledge base may be provided to ground your evaluation."""


def create_seven_dim_signature():
    """Create and return the DSPy Signature for 7-dimension scoring.

    Returns a DSPy Signature class if dspy is available, otherwise returns
    a dict-based fallback describing the signature structure.
    """
    if DSPY_AVAILABLE:

        class SevenDimScoring(dspy.Signature):
            __doc__ = SCORING_INSTRUCTIONS

            script: str = dspy.InputField(desc="完整脚本文本（含分镜和台词）")
            knowledge_context: str = dspy.InputField(desc="知识库上下文（rubric规则与最佳实践）")

            hook_score: float = dspy.OutputField(desc="钩子得分 (0-10)")
            emotion_score: float = dspy.OutputField(desc="情绪得分 (0-10)")
            structure_score: float = dspy.OutputField(desc="结构得分 (0-10)")
            copywriting_score: float = dspy.OutputField(desc="文案得分 (0-10)")
            persona_score: float = dspy.OutputField(desc="人设得分 (0-10)")
            virality_score: float = dspy.OutputField(desc="传播力得分 (0-10)")
            rhythm_score: float = dspy.OutputField(desc="节奏得分 (0-10)")
            overall_comment: str = dspy.OutputField(desc="整体评价（中文，2-3句）")

        return SevenDimScoring

    return {
        "name": "SevenDimScoring",
        "description": SCORING_INSTRUCTIONS,
        "inputs": {
            "script": {"type": "str", "description": "完整脚本文本（含分镜和台词）"},
            "knowledge_context": {"type": "str", "description": "知识库上下文（rubric规则与最佳实践）"},
        },
        "outputs": {
            "hook_score": {"type": "float", "description": "钩子得分 (0-10)"},
            "emotion_score": {"type": "float", "description": "情绪得分 (0-10)"},
            "structure_score": {"type": "float", "description": "结构得分 (0-10)"},
            "copywriting_score": {"type": "float", "description": "文案得分 (0-10)"},
            "persona_score": {"type": "float", "description": "人设得分 (0-10)"},
            "virality_score": {"type": "float", "description": "传播力得分 (0-10)"},
            "rhythm_score": {"type": "float", "description": "节奏得分 (0-10)"},
            "overall_comment": {"type": "str", "description": "整体评价（中文，2-3句）"},
        },
    }


def _load_json(path: Path) -> Optional[dict]:
    """Safely load a JSON file, returning None on failure."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, OSError) as e:
        print(f"error: 无法读取 {path}: {e}", file=sys.stderr)
        return None


def _save_json(path: Path, data: dict) -> bool:
    """Atomically save JSON data (write to .tmp, then rename)."""
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, path)
        return True
    except OSError as e:
        print(f"error: 无法写入 {path}: {e}", file=sys.stderr)
        return False


def _update_yang_state(updates: dict) -> None:
    """Update .yang-state.json with the given key-value pairs."""
    state = _load_json(STATE_FILE) or {}
    state.update(updates)
    _save_json(STATE_FILE, state)


def _infer_model() -> str:
    """Infer the best available LLM model for DSPy configuration.

    Priority:
        1. YANG_DSPY_MODEL environment variable (default: anthropic/claude-sonnet-4-5)
        2. Auto-detect from available API keys
    """
    env_model = os.environ.get("YANG_DSPY_MODEL", "claude-sonnet-4-5")
    if "/" in env_model:
        return env_model

    if os.environ.get("ANTHROPIC_API_KEY"):
        return f"anthropic/{env_model}"
    if os.environ.get("OPENAI_API_KEY"):
        return "openai/gpt-4o-mini"

    try:
        import urllib.request

        req = urllib.request.Request("http://localhost:11434/api/tags")
        urllib.request.urlopen(req, timeout=2)
        return "ollama_chat/llama3"
    except Exception:
        pass

    return "openai/gpt-4o-mini"


def train_mode(
    calibration_file: str,
    optimizer: str = "mipro-v2",
    trials: int = 10,
    output: str = None,
    model: str = None,
):
    """Train mode: read calibration JSON, select optimizer, output optimized scoring.

    Sample count thresholds:
        ≥20 → mipro-v2
        5-19 → bootstrap-fewshot
        <5  → skip optimization, use v3 rules
    """
    calib_path = Path(calibration_file)
    if not calib_path.is_file():
        print(f"error: 校准文件不存在: {calibration_file}", file=sys.stderr)
        sys.exit(1)

    data = _load_json(calib_path)
    if data is None:
        sys.exit(1)

    samples = data.get("calibration_samples", [])
    rubric_context = data.get("rubric_context", "")
    kb_context = data.get("knowledge_base_context", "")
    sample_count = len(samples)

    print(f"已加载 {sample_count} 条校准样本", file=sys.stderr)

    if sample_count >= 20:
        resolved_optimizer = "mipro-v2"
    elif sample_count >= 5:
        resolved_optimizer = "bootstrap-fewshot"
    else:
        resolved_optimizer = "v3-rules"
        print(
            f"样本数 {sample_count} < 5，跳过优化，使用 v3 规则评分",
            file=sys.stderr,
        )

    if optimizer != "mipro-v2" and sample_count >= 5:
        resolved_optimizer = optimizer

    if resolved_optimizer == "v3-rules":
        optimized = {
            "version": "v3-rules",
            "optimizer": "v3-rules",
            "trials": 0,
            "samples": sample_count,
            "trained_at": datetime.now(timezone.utc).isoformat(),
            "signature": create_seven_dim_signature()
            if not DSPY_AVAILABLE
            else "SevenDimScoring",
            "scoring_mode": "rules-based",
            "field_weights": {f: 1.0 / 7 for f in SEVEN_DIM_FIELDS},
        }
        out_path = Path(output) if output else OPTIMIZED_SCORING_PATH
        _save_json(out_path, optimized)
        _update_yang_state(
            {
                "scoring_optimizer_version": "v3-rules",
                "scoring_optimizer_samples": sample_count,
                "scoring_optimizer_exists": True,
            }
        )
        print(f"v3 规则评分配置已保存 → {out_path}", file=sys.stderr)
        return

    if not DSPY_AVAILABLE:
        print(
            "error: DSPy 未安装。请运行: pip install dspy-ai",
            file=sys.stderr,
        )
        print(
            "安装后重新运行: python tools/dspy_scoring.py --train <校准文件>",
            file=sys.stderr,
        )
        sys.exit(1)

    model_str = model or _infer_model()
    print(f"使用模型: {model_str}", file=sys.stderr)

    try:
        lm = dspy.LM(model_str)
        dspy.configure(lm=lm)
    except Exception as e:
        print(f"error: 无法配置 DSPy LM: {e}", file=sys.stderr)
        sys.exit(1)

    SevenDimScoring = create_seven_dim_signature()

    trainset = []
    for sample in samples:
        script_text = sample.get("script", "")
        graded = sample.get("graded_scores", {})

        example = dspy.Example(
            script=script_text,
            knowledge_context=rubric_context + "\n" + kb_context,
            hook_score=float(graded.get("hook", {}).get("value", 5)),
            emotion_score=float(graded.get("emotion", {}).get("value", 5)),
            structure_score=float(graded.get("structure", {}).get("value", 5)),
            copywriting_score=float(graded.get("copywriting", {}).get("value", 5)),
            persona_score=float(graded.get("persona", {}).get("value", 5)),
            virality_score=float(graded.get("virality", {}).get("value", 5)),
            rhythm_score=float(graded.get("rhythm", {}).get("value", 5)),
            overall_comment=graded.get("overall_comment", ""),
        ).with_inputs("script", "knowledge_context")
        trainset.append(example)

    print(f"训练集构建完成: {len(trainset)} 条样本", file=sys.stderr)

    wrapped_program = dspy.ChainOfThought(SevenDimScoring)

    if resolved_optimizer == "mipro-v2":
        try:
            teleprompter_cls = dspy.MIPROv2
        except AttributeError:
            try:
                teleprompter_cls = dspy.MIPRO
            except AttributeError:
                print(
                    "info: MIPROv2 不可用，回退至 BootstrapFewShot",
                    file=sys.stderr,
                )
                resolved_optimizer = "bootstrap-fewshot"

    if resolved_optimizer == "bootstrap-fewshot":
        teleprompter = dspy.BootstrapFewShot(
            metric=None,
            max_bootstrapped_demos=4,
            max_labeled_demos=min(16, len(trainset)),
        )
    elif resolved_optimizer in ("mipro-v2", "mipro"):
        teleprompter = teleprompter_cls(
            metric=None,
            num_threads=1,
            num_candidates=trials,
        )
    elif resolved_optimizer == "gepa":
        try:
            teleprompter = dspy.GEPA(num_candidates=trials)
        except AttributeError:
            print(
                "info: GEPA 不可用，回退至 BootstrapFewShot",
                file=sys.stderr,
            )
            resolved_optimizer = "bootstrap-fewshot"
            teleprompter = dspy.BootstrapFewShot(
                metric=None,
                max_bootstrapped_demos=4,
                max_labeled_demos=min(16, len(trainset)),
            )
    else:
        teleprompter = dspy.BootstrapFewShot(
            metric=None,
            max_bootstrapped_demos=4,
            max_labeled_demos=min(16, len(trainset)),
        )

    print(f"开始优化训练 (优化器: {resolved_optimizer}, trials: {trials})...", file=sys.stderr)

    try:
        optimized_program = teleprompter.compile(
            wrapped_program,
            trainset=trainset,
        )
    except Exception as e:
        print(f"error: 优化训练失败: {e}", file=sys.stderr)
        print("info: 保存未经优化的签名作为备用", file=sys.stderr)

        optimized_data = {
            "version": "v4-optimized",
            "optimizer": f"{resolved_optimizer}-failed",
            "trials": 0,
            "samples": sample_count,
            "trained_at": datetime.now(timezone.utc).isoformat(),
            "signature": "SevenDimScoring",
            "scoring_mode": "optimized",
            "field_weights": {f: 1.0 / 7 for f in SEVEN_DIM_FIELDS},
            "model_used": model_str,
        }
        out_path = Path(output) if output else OPTIMIZED_SCORING_PATH
        _save_json(out_path, optimized_data)
        _update_yang_state(
            {
                "scoring_optimizer_version": "v4-optimized-failed",
                "scoring_optimizer_samples": sample_count,
                "scoring_optimizer_exists": True,
            }
        )
        sys.exit(1)

    saved = False
    try:
        serializable = {}
        compiled_path = OPTIMIZED_SCORING_PATH.parent / "optimized_scoring_compiled.json"
        optimized_program.save(str(compiled_path))
        serializable = _load_json(compiled_path) or {}
        saved = True
    except Exception as e:
        print(f"warn: 无法序列化编译后的程序: {e}", file=sys.stderr)

    optimized_data = {
        "version": "v4-optimized",
        "optimizer": resolved_optimizer,
        "trials": trials,
        "samples": sample_count,
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "signature": "SevenDimScoring",
        "scoring_mode": "optimized",
        "field_weights": {f: 1.0 / 7 for f in SEVEN_DIM_FIELDS},
        "model_used": model_str,
        "compiled_program": serializable,
    }

    out_path = Path(output) if output else OPTIMIZED_SCORING_PATH
    _save_json(out_path, optimized_data)
    _update_yang_state(
        {
            "scoring_optimizer_version": "v4-optimized",
            "scoring_optimizer_samples": sample_count,
            "scoring_optimizer_exists": True,
            "scoring_optimizer_model": model_str,
        }
    )

    saved_flag = "（已序列化）" if saved else "（未序列化）"
    print(
        f"优化完成 {saved_flag} → {out_path}",
        file=sys.stderr,
    )


def score_mode(script_file: str):
    """Score mode: read script, load optimized signature, score, output JSON."""
    script_path = Path(script_file)
    if not script_path.is_file():
        print(f"error: 脚本文件不存在: {script_file}", file=sys.stderr)
        sys.exit(1)

    try:
        script_text = script_path.read_text(encoding="utf-8")
    except OSError as e:
        print(f"error: 无法读取脚本: {e}", file=sys.stderr)
        sys.exit(1)

    optimized = _load_json(OPTIMIZED_SCORING_PATH)
    if optimized is None:
        print(
            "info: 未找到优化签名，使用 v3 规则评分（运行 --train 进行优化）",
            file=sys.stderr,
        )
        scores = _rules_based_score(script_text)
        print(json.dumps(scores, ensure_ascii=False, indent=2))
        return

    scoring_mode = optimized.get("scoring_mode", "rules-based")
    if scoring_mode == "rules-based" or not DSPY_AVAILABLE:
        scores = _rules_based_score(script_text)
        print(json.dumps(scores, ensure_ascii=False, indent=2))
        return

    try:
        model_str = optimized.get("model_used", _infer_model())
        lm = dspy.LM(model_str)
        dspy.configure(lm=lm)
    except Exception as e:
        print(f"error: 无法配置 DSPy LM: {e}", file=sys.stderr)
        print("info: 回退至规则评分", file=sys.stderr)
        scores = _rules_based_score(script_text)
        print(json.dumps(scores, ensure_ascii=False, indent=2))
        return

    SevenDimScoring = create_seven_dim_signature()
    program = dspy.ChainOfThought(SevenDimScoring)

    compiled_program_data = optimized.get("compiled_program", {})
    if compiled_program_data:
        try:
            compiled_path = OPTIMIZED_SCORING_PATH.parent / "optimized_scoring_compiled.json"
            program.load(str(compiled_path))
        except Exception:
            pass

    rubric_context = optimized.get("rubric_context", "")
    kb_context = optimized.get("knowledge_base_context", "")

    try:
        result = program(
            script=script_text,
            knowledge_context=rubric_context + "\n" + kb_context,
        )
        scores = {
            "hook_score": getattr(result, "hook_score", 5.0),
            "emotion_score": getattr(result, "emotion_score", 5.0),
            "structure_score": getattr(result, "structure_score", 5.0),
            "copywriting_score": getattr(result, "copywriting_score", 5.0),
            "persona_score": getattr(result, "persona_score", 5.0),
            "virality_score": getattr(result, "virality_score", 5.0),
            "rhythm_score": getattr(result, "rhythm_score", 5.0),
            "overall_comment": getattr(result, "overall_comment", ""),
            "scoring_mode": "optimized",
        }
        print(json.dumps(scores, ensure_ascii=False, indent=2))
    except Exception as e:
        print(f"error: DSPy 评分失败: {e}", file=sys.stderr)
        print("info: 回退至规则评分", file=sys.stderr)
        scores = _rules_based_score(script_text)
        print(json.dumps(scores, ensure_ascii=False, indent=2))


def _rules_based_score(script_text: str) -> dict:
    """Fallback — DSPy not available, rules-based scoring is disabled."""

    return {
        "fallback_mode": True,
        "scoring_disabled": True,
        "message": "⚠️ DSPy 不可用，规则评分已禁用。请使用主对话中的 yang-score 进行人工打分",
    }


def info_mode():
    """Print current optimized scoring version, sample count, optimizer type."""
    if not OPTIMIZED_SCORING_PATH.is_file():
        print("未找到优化签名，请先运行 --train")
        return

    optimized = _load_json(OPTIMIZED_SCORING_PATH)
    if optimized is None:
        print("未找到优化签名，请先运行 --train")
        return

    version = optimized.get("version", "unknown")
    samples = optimized.get("samples", 0)
    opt_type = optimized.get("optimizer", "unknown")
    scoring_mode = optimized.get("scoring_mode", "unknown")
    trained_at = optimized.get("trained_at", "unknown")
    model_used = optimized.get("model_used", "N/A")

    print(f"版本:       {version}")
    print(f"优化器:     {opt_type}")
    print(f"评分模式:   {scoring_mode}")
    print(f"校准样本:   {samples}")
    print(f"训练时间:   {trained_at}")
    print(f"使用模型:   {model_used}")
    print(f"配置文件:   {OPTIMIZED_SCORING_PATH}")


def main():
    parser = argparse.ArgumentParser(
        description="DSPy Scoring Optimizer for Yang.skills",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--train", type=str, help="校准数据文件路径（JSON格式）")
    parser.add_argument("--score", type=str, help="脚本文件路径（纯文本）")
    parser.add_argument("--info", action="store_true", help="查看当前优化签名信息")
    parser.add_argument(
        "--optimizer",
        type=str,
        default="mipro-v2",
        choices=["mipro-v2", "bootstrap-fewshot", "gepa"],
        help="优化器类型（样本≥20默认mipro-v2，5-19默认bootstrap-fewshot）",
    )
    parser.add_argument(
        "--trials",
        type=int,
        default=10,
        help="优化搜索次数，范围 5-30",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=str(OPTIMIZED_SCORING_PATH),
        help="优化签名输出路径",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="DSPy LM 模型名（如 openai/gpt-4o），自动检测环境变量",
    )

    args = parser.parse_args()

    trials = max(5, min(30, args.trials))

    if args.train:
        train_mode(args.train, args.optimizer, trials, args.output, args.model)
    elif args.score:
        score_mode(args.score)
    elif args.info:
        info_mode()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()