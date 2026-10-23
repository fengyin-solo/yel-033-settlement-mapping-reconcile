"""Acceptance tests for hidden-channel fingerprint reconciliation."""

import copy
import json
import os
import subprocess
import sys

import pytest


ENTRY = os.environ.get("SETTLEMENT_MAPPING_ENTRY", "/app/settlement_mapping_reconcile.py")
PROFILES = [{'ledger_id': 'SETTLE-A', 'fingerprint': [1.42, 0.7, 0.021]},
 {'ledger_id': 'SETTLE-B', 'fingerprint': [1.18, 0.82, 0.016]},
 {'ledger_id': 'SETTLE-C', 'fingerprint': [1.76, 0.63, 0.032]},
 {'ledger_id': 'SETTLE-D', 'fingerprint': [1.33, 0.77, 0.024]},
 {'ledger_id': 'SETTLE-E', 'fingerprint': [1.54, 0.89, 0.019]},
 {'ledger_id': 'SETTLE-F', 'fingerprint': [1.09, 0.68, 0.028]},
 {'ledger_id': 'SETTLE-G', 'fingerprint': [1.91, 0.74, 0.014]},
 {'ledger_id': 'SETTLE-H', 'fingerprint': [1.27, 0.95, 0.036]},
 {'ledger_id': 'SETTLE-I', 'fingerprint': [1.63, 0.58, 0.022]},
 {'ledger_id': 'SETTLE-J', 'fingerprint': [1.47, 0.86, 0.031]}]
READINGS = [{'slot': 'CH-3',
  'gross_notional': 2000.0,
  'net_cash': 1408.4507042253522,
  'collateral_ratio': 0.6975585450921773,
  'trade_count': 3.50175,
  'funding_bps': 35.0},
 {'slot': 'CH-10',
  'gross_notional': 2000.0,
  'net_cash': 1694.9152542372883,
  'collateral_ratio': 0.8171400099651219,
  'trade_count': 2.6679999999999997,
  'funding_bps': 35.0},
 {'slot': 'CH-6',
  'gross_notional': 2000.0,
  'net_cash': 1136.3636363636363,
  'collateral_ratio': 0.6278026905829596,
  'trade_count': 5.335999999999999,
  'funding_bps': 35.0},
 {'slot': 'CH-13',
  'gross_notional': 2000.0,
  'net_cash': 1503.7593984962405,
  'collateral_ratio': 0.7673143996013951,
  'trade_count': 4.002,
  'funding_bps': 35.0},
 {'slot': 'CH-9',
  'gross_notional': 2000.0,
  'net_cash': 1298.7012987012986,
  'collateral_ratio': 0.8868958644743398,
  'trade_count': 3.16825,
  'funding_bps': 35.0},
 {'slot': 'CH-5',
  'gross_notional': 2000.0,
  'net_cash': 1834.8623853211009,
  'collateral_ratio': 0.6776283009466866,
  'trade_count': 4.669,
  'funding_bps': 35.0},
 {'slot': 'CH-12',
  'gross_notional': 2000.0,
  'net_cash': 1047.1204188481677,
  'collateral_ratio': 0.7374190333831588,
  'trade_count': 2.3345,
  'funding_bps': 35.0},
 {'slot': 'CH-8',
  'gross_notional': 2000.0,
  'net_cash': 1574.8031496062993,
  'collateral_ratio': 0.946686596910812,
  'trade_count': 6.003,
  'funding_bps': 35.0},
 {'slot': 'CH-4',
  'gross_notional': 2000.0,
  'net_cash': 1226.993865030675,
  'collateral_ratio': 0.5779770802192327,
  'trade_count': 3.6685,
  'funding_bps': 35.0},
 {'slot': 'CH-11',
  'gross_notional': 2000.0,
  'net_cash': 1360.544217687075,
  'collateral_ratio': 0.8570004982561036,
  'trade_count': 5.16925,
  'funding_bps': 35.0}]
EXPECTED_ROWS = [{'slot': 'CH-10', 'ledger_id': 'SETTLE-B', 'residual': 0.0},
 {'slot': 'CH-11', 'ledger_id': 'SETTLE-J', 'residual': 0.0},
 {'slot': 'CH-12', 'ledger_id': 'SETTLE-G', 'residual': 0.0},
 {'slot': 'CH-13', 'ledger_id': 'SETTLE-D', 'residual': 0.0},
 {'slot': 'CH-3', 'ledger_id': 'SETTLE-A', 'residual': 0.0},
 {'slot': 'CH-4', 'ledger_id': 'SETTLE-I', 'residual': 0.0},
 {'slot': 'CH-5', 'ledger_id': 'SETTLE-F', 'residual': 0.0},
 {'slot': 'CH-6', 'ledger_id': 'SETTLE-C', 'residual': 0.0},
 {'slot': 'CH-8', 'ledger_id': 'SETTLE-H', 'residual': 0.0},
 {'slot': 'CH-9', 'ledger_id': 'SETTLE-E', 'residual': 0.0}]
OUTPUT_KEYS = ['batch_id', 'status', 'ledger_assignments', 'total_residual', 'accepted', 'diagnostic']
LEDGER_KEYS = ['batch_id', 'input_sha256', 'result_sha256', 'total_residual']


def base_payload():
    return {
        "batch_id": "SETTLE-STD-7",
        "limits": {"max_slots": 12, "residual_ceiling": 0.02},
        "profiles": copy.deepcopy(PROFILES),
        "readings": copy.deepcopy(READINGS),
    }


def invoke(tmp_path, payload=None, ledger=None, raw=None, output_name="result.json"):
    source = tmp_path / "readings.json"
    target = tmp_path / output_name
    if raw is None:
        raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n"
    source.write_bytes(raw.encode("utf-8"))
    command = [sys.executable, ENTRY, str(source), str(target)]
    if ledger is not None:
        command.append(str(ledger))
    completed = subprocess.run(command, capture_output=True, text=True, timeout=30)
    return completed, source, target


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_success_writes_aligned_output_quietly(tmp_path):
    """题面：「成功时 stdout 和 stderr 都必须为空，结果文件是唯一成功信号。」"""
    result, _, output = invoke(tmp_path, base_payload())
    assert result.returncode == 0
    assert result.stdout == "" and result.stderr == ""
    assert output.is_file()


def test_global_assignment_is_minimum_residual(tmp_path):
    """题面：「清算通道必须采用总指纹误差最小的全局对应，而不是按读入顺序配对。」"""
    result, _, output = invoke(tmp_path, base_payload())
    document = read(output)
    assert result.returncode == 0
    assert [(row["slot"], row["ledger_id"]) for row in document["ledger_assignments"]] == [(row["slot"], row["ledger_id"]) for row in EXPECTED_ROWS]
    assert [row["residual"] for row in document["ledger_assignments"]] == pytest.approx([row["residual"] for row in EXPECTED_ROWS], abs=1e-12)


def test_assignment_rows_have_exact_fields(tmp_path):
    """题面：「每条ledger_assignments记录恰好包含 slot、ledger_id 和 residual 三个键。」"""
    result, _, output = invoke(tmp_path, base_payload())
    document = read(output)
    assert result.returncode == 0
    assert all(set(row) == {"slot", "ledger_id", "residual"} for row in document["ledger_assignments"])


def test_output_has_exact_top_level_keys(tmp_path):
    """题面：「结果根对象恰好包含 batch_id、status、ledger_assignments、total_residual、accepted 和 diagnostic 六个键。」"""
    result, _, output = invoke(tmp_path, base_payload())
    document = read(output)
    assert result.returncode == 0
    assert list(document) == OUTPUT_KEYS


def test_output_is_compact_utf8_with_single_lf(tmp_path):
    """题面：「结果文件使用紧凑 UTF-8 JSON，末尾只有一个 LF。」"""
    result, _, output = invoke(tmp_path, base_payload())
    raw = output.read_bytes()
    assert result.returncode == 0
    assert raw.endswith(b"\n") and not raw.endswith(b"\n\n")
    assert b": " not in raw and b", " not in raw


def test_total_residual_matches_assignment(tmp_path):
    """题面：「total_residual 是最终对应中所有 residual 之和。」"""
    result, _, output = invoke(tmp_path, base_payload())
    document = read(output)
    total = sum(row["residual"] for row in document["ledger_assignments"])
    assert result.returncode == 0
    assert document["total_residual"] == pytest.approx(total, abs=1e-12)
    assert document["total_residual"] == pytest.approx(0.0, abs=1e-10)


def test_ceiling_accepts_inside_case(tmp_path):
    """题面：「总误差不超过 residual_ceiling 时 accepted 为 true。」"""
    payload = base_payload()
    payload["limits"]["residual_ceiling"] = 1.0
    payload["profiles"][0]["fingerprint"] = [value * 1.04 for value in payload["profiles"][0]["fingerprint"]]
    result, _, output = invoke(tmp_path, payload)
    document = read(output)
    assert result.returncode == 0 and document["accepted"] is True
    assert document["status"] == "ledgers_reconciled"


def test_ceiling_quarantines_first_outside_value(tmp_path):
    """题面：「总误差超过 residual_ceiling 时仍保留结果，但 accepted 为 false 且 status 为 quarantined。」"""
    payload = base_payload()
    payload["limits"]["residual_ceiling"] = 0.0001
    payload["profiles"][0]["fingerprint"] = [value * 1.04 for value in payload["profiles"][0]["fingerprint"]]
    result, _, output = invoke(tmp_path, payload)
    document = read(output)
    assert result.returncode == 0 and document["accepted"] is False
    assert document["status"] == "quarantined"


def test_missing_top_level_key_is_refused(tmp_path):
    """题面：「日终输入最外层的成员集合由清算批号 `batch_id`、本批限额 `limits`、账户档案 `profiles` 和现场读数 `readings` 组成。」"""
    payload = base_payload()
    payload.pop("limits")
    result, _, output = invoke(tmp_path, payload)
    assert result.returncode == 1 and result.stderr == "结算拒收: BAD_SETTLEMENT\n" and not output.exists()


def test_extra_top_level_key_is_refused(tmp_path):
    """题面：「顶层多键时以 1 结束并输出 结算拒收: BAD_SETTLEMENT。」"""
    payload = base_payload()
    payload["memo"] = "shift"
    result, _, output = invoke(tmp_path, payload)
    assert result.returncode == 1 and result.stderr == "结算拒收: BAD_SETTLEMENT\n" and not output.exists()


def test_duplicate_top_level_key_is_refused(tmp_path):
    """题面：「同一对象出现重复键时按输入损坏处理并输出 结算拒收: BAD_SETTLEMENT。」"""
    payload = base_payload()
    raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    raw = raw.replace('"batch_id":"', '"batch_id":"duplicate", "batch_id":"', 1) + "\n"
    result, _, output = invoke(tmp_path, raw=raw)
    assert result.returncode == 1 and result.stderr == "结算拒收: BAD_SETTLEMENT\n" and not output.exists()


def test_boolean_numeric_is_refused(tmp_path):
    """题面：「数值字段使用布尔值时不得当作有限数并输出 结算拒收: BAD_SETTLEMENT。」"""
    payload = base_payload()
    payload["readings"][0]["gross_notional"] = True
    result, _, output = invoke(tmp_path, payload)
    assert result.returncode == 1 and result.stderr == "结算拒收: BAD_SETTLEMENT\n" and not output.exists()


def test_profile_fingerprint_length_is_refused(tmp_path):
    """题面：「每个指纹必须恰好有三个正有限分量，否则输出 结算拒收: BAD_SETTLEMENT。」"""
    payload = base_payload()
    payload["profiles"][0]["fingerprint"].pop()
    result, _, output = invoke(tmp_path, payload)
    assert result.returncode == 1 and result.stderr == "结算拒收: BAD_SETTLEMENT\n" and not output.exists()


def test_duplicate_slot_is_refused(tmp_path):
    """题面：「两个清算通道使用同名 slot 时输出 结算拒收: BAD_SETTLEMENT。」"""
    payload = base_payload()
    payload["readings"][1]["slot"] = payload["readings"][0]["slot"]
    result, _, output = invoke(tmp_path, payload)
    assert result.returncode == 1 and result.stderr == "结算拒收: BAD_SETTLEMENT\n" and not output.exists()


def test_ledger_has_exact_shape_and_is_idempotent(tmp_path):
    """题面：「完全相同的输入和结果再次运行时，留痕簿字节保持不变。」"""
    ledger = tmp_path / "trail.jsonl"
    result, _, output = invoke(tmp_path, payload=base_payload(), ledger=ledger)
    first = ledger.read_bytes()
    second, _, _ = invoke(tmp_path, payload=base_payload(), ledger=ledger)
    item = json.loads(first)
    assert result.returncode == 0 and second.returncode == 0
    assert list(item) == LEDGER_KEYS and first.endswith(b"\n")
    assert ledger.read_bytes() == first and second.stdout == "" and second.stderr == ""


def test_different_result_appends_one_ledger_line(tmp_path):
    """题面：「不同结果成功产生后，留痕簿按成功顺序追加一行。」"""
    ledger = tmp_path / "trail.jsonl"
    first, _, _ = invoke(tmp_path, payload=base_payload(), ledger=ledger)
    changed = base_payload()
    changed["batch_id"] = "SETTLE-STD-8"
    second, _, _ = invoke(tmp_path, payload=changed, ledger=ledger)
    assert first.returncode == 0 and second.returncode == 0
    assert len(ledger.read_bytes().splitlines()) == 2
    assert ledger.read_bytes().endswith(b"\n")


def test_ledger_path_equal_to_output_is_refused(tmp_path):
    """题面：「留痕簿路径与结果路径相同时输出 结算簿拒收: BAD_SETTLEMENT_LEDGER。」"""
    payload = base_payload()
    source = tmp_path / "readings.json"
    target = tmp_path / "same.json"
    source.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")
    result = subprocess.run([sys.executable, ENTRY, str(source), str(target), str(target)], capture_output=True, text=True, timeout=30)
    assert result.returncode == 1 and result.stderr == "结算簿拒收: BAD_SETTLEMENT_LEDGER\n" and not target.exists()


def test_io_failure_preserves_existing_target(tmp_path):
    """题面：「结果目标不可写时输出 归档失败: SETTLEMENT_IO，既有结果保持原样。」"""
    target = tmp_path / "occupied"
    target.mkdir()
    source = tmp_path / "readings.json"
    source.write_text(json.dumps(base_payload(), separators=(",", ":")), encoding="utf-8")
    result = subprocess.run([sys.executable, ENTRY, str(source), str(target)], capture_output=True, text=True, timeout=30)
    assert result.returncode == 1 and result.stderr == "归档失败: SETTLEMENT_IO\n"
    assert target.exists() and target.is_dir() and not any(target.iterdir()) and "traceback" not in result.stderr.lower()


def test_wrong_argument_count_is_refused(tmp_path):
    """题面：「命令行没有按声明给出输入与结果路径时，以 1 结束并输出 结算拒收: BAD_SETTLEMENT。」"""
    target = tmp_path / "result.json"
    result = subprocess.run([sys.executable, ENTRY], capture_output=True, text=True, timeout=30)
    assert result.returncode == 1 and result.stderr == "结算拒收: BAD_SETTLEMENT\n" and not target.exists()
