"""Check completed local USB paths and the exact branches retained beside them."""

import copy
import math
from collections import defaultdict, deque

from center_pcie_paths import check_paths


SCOPE = "local USB paths and connector branches"
ROUTED_TYPES = {"PCB_TRACK", "PCB_ARC", "PCB_VIA"}
ITEM_TYPES = ROUTED_TYPES | {"PAD"}
GEOMETRY_FIELDS = (
    "id", "type", "net", "start", "end", "width", "layers", "drill",
    "center", "mid", "ref", "number", "size", "angle", "box",
)


def geometry(item):
    """Copy the native geometry fields protected by a reviewed path contract."""
    return {key: copy.deepcopy(item[key]) for key in GEOMETRY_FIELDS if key in item}


class _SchemaError(ValueError):
    def __init__(self, path, message, kind="schema_error"):
        super().__init__(message)
        self.finding = {"kind": kind, "path": path, "message": message}


def _require(condition, path, message, kind="schema_error"):
    if not condition:
        raise _SchemaError(path, message, kind)


def _mapping(value, path):
    _require(isinstance(value, dict), path, "expected an object")
    return value


def _text(value, path):
    _require(isinstance(value, str) and bool(value), path, "expected a nonempty string")
    return value


def _strings(value, path, nonempty=False):
    _require(isinstance(value, list), path, "expected a list of strings")
    for index, item in enumerate(value):
        _text(item, f"{path}[{index}]")
    _require(len(value) == len(set(value)), path, "duplicate entries are not allowed")
    _require(not nonempty or bool(value), path, "the list cannot be empty")
    return value


def _number(value, path, minimum=None):
    _require(type(value) in (int, float) and math.isfinite(value), path,
             "expected a finite number")
    _require(minimum is None or value >= minimum, path,
             f"expected a number greater than or equal to {minimum}")


def _vector(value, size, path):
    _require(isinstance(value, list) and len(value) == size, path,
             f"expected {size} coordinates")
    for index, coordinate in enumerate(value):
        _number(coordinate, f"{path}[{index}]")


def _definitions(definitions, path, nonempty=False):
    _require(isinstance(definitions, list), path, "expected a list of signal paths")
    _require(not nonempty or bool(definitions), path, "at least one path is required")
    names = set()
    all_nets = set()
    for index, definition in enumerate(definitions):
        here = f"{path}[{index}]"
        definition = _mapping(definition, here)
        name = _text(definition.get("name"), here + ".name")
        _require(name not in names, here + ".name", "path names must be unique")
        names.add(name)
        nets = _mapping(definition.get("nets"), here + ".nets")
        _require(set(nets) == {"P", "N"}, here + ".nets", "expected P and N lists")
        for polarity in ("P", "N"):
            _strings(nets[polarity], here + ".nets." + polarity, nonempty=True)
        expected_nets = set(nets["P"]) | set(nets["N"])
        _require(not set(nets["P"]) & set(nets["N"]), here + ".nets",
                 "a net cannot belong to both polarities")
        endpoints = _mapping(definition.get("endpoints"), here + ".endpoints")
        _require(set(endpoints) == expected_nets, here + ".endpoints",
                 "endpoint keys must match the path nets")
        for net, pads in endpoints.items():
            _strings(pads, here + ".endpoints." + net)
            _require(len(pads) == 2, here + ".endpoints." + net,
                     "each selected net needs exactly two endpoint pads")
        _number(definition.get("max_pn_difference_mm"), here + ".max_pn_difference_mm", 0)
        count = definition.get("via_transition_count")
        _require(type(count) is int and count >= 0, here + ".via_transition_count",
                 "expected a nonnegative integer")
        if "post_cap_nets" in definition:
            post_cap = _mapping(definition["post_cap_nets"], here + ".post_cap_nets")
            _require(set(post_cap) == {"P", "N"}, here + ".post_cap_nets",
                     "expected P and N post-capacitor nets")
            for polarity, net in post_cap.items():
                _require(net in nets[polarity], here + ".post_cap_nets." + polarity,
                         "post-capacitor net must belong to that polarity")
            _number(definition.get("max_post_cap_path_with_via_mm"),
                    here + ".max_post_cap_path_with_via_mm", 0)
        all_nets.update(expected_nets)
    return all_nets


def _validate_contract(spec):
    spec = _mapping(spec, "spec")
    _require(type(spec.get("schema_version")) is int and spec["schema_version"] == 1,
             "spec.schema_version", "only schema version 1 is supported")
    direct_nets = _definitions(spec.get("direct_signal_paths"), "spec.direct_signal_paths")
    pad_sets = _mapping(spec.get("full_native_pad_sets"), "spec.full_native_pad_sets")
    for net, pads in pad_sets.items():
        _text(net, "spec.full_native_pad_sets key")
        _strings(pads, "spec.full_native_pad_sets." + net, nonempty=True)
    cases = spec.get("selected_cases")
    _require(isinstance(cases, list), "spec.selected_cases", "expected a list")
    names = set()
    for index, case in enumerate(cases):
        here = f"spec.selected_cases[{index}]"
        case = _mapping(case, here)
        name = _text(case.get("name"), here + ".name")
        _require(name not in names, here + ".name", "selection names must be unique")
        names.add(name)
        nets = _definitions(case.get("signal_paths"), here + ".signal_paths", nonempty=True)
        _require(nets <= set(pad_sets), here + ".signal_paths",
                 "every selected net needs a complete native pad-set assertion")
        _strings(case.get("include_native_item_uuids"), here + ".include_native_item_uuids",
                 nonempty=True)
    _require(bool(direct_nets) or bool(cases), "spec", "at least one path is required")
    expected = _mapping(spec.get("expected_native_geometry"), "spec.expected_native_geometry")
    for uid, item in expected.items():
        _text(uid, "spec.expected_native_geometry key")
        _mapping(item, "spec.expected_native_geometry." + uid)
        _require(item.get("id") == uid, "spec.expected_native_geometry." + uid,
                 "geometry id must match its key")
        _text(item.get("net"), "spec.expected_native_geometry." + uid + ".net")
        _require(item.get("net") in pad_sets, "spec.expected_native_geometry." + uid,
                 "reviewed geometry must belong to an asserted multi-terminal net")
    branches = spec.get("declared_intentional_branches")
    _require(isinstance(branches, list), "spec.declared_intentional_branches", "expected a list")
    names = set()
    for index, branch in enumerate(branches):
        here = f"spec.declared_intentional_branches[{index}]"
        branch = _mapping(branch, here)
        name = _text(branch.get("name"), here + ".name")
        _require(name not in names, here + ".name", "branch names must be unique")
        names.add(name)
        _text(branch.get("net"), here + ".net")
        _require(branch.get("net") in pad_sets, here + ".net",
                 "branch net needs a complete native pad-set assertion")
        _text(branch.get("anchor_pad_uuid"), here + ".anchor_pad_uuid")
        _text(branch.get("anchor_pad"), here + ".anchor_pad")
        pads = _strings(branch.get("expected_native_pad_component"),
                        here + ".expected_native_pad_component", nonempty=True)
        _require(set(pads) <= set(pad_sets[branch["net"]]), here,
                 "branch component pads must belong to its declared net")
        _require(branch["anchor_pad"] in pads, here,
                 "the expected component must contain the branch anchor")
        _strings(branch.get("routed_item_uuids"), here + ".routed_item_uuids", nonempty=True)
    return direct_nets | set(pad_sets)


def _validate_data(data, scoped_nets):
    data = _mapping(data, "data")
    _text(data.get("source_sha256"), "data.source_sha256")
    items = data.get("items")
    _require(isinstance(items, list), "data.items", "expected a list")
    ids = set()
    for index, item in enumerate(items):
        here = f"data.items[{index}]"
        item = _mapping(item, here)
        uid = _text(item.get("id"), here + ".id")
        _require(uid not in ids, here + ".id", "native item ids must be unique",
                 "duplicate_native_id")
        ids.add(uid)
        _text(item.get("type"), here + ".type")
        _require(isinstance(item.get("net"), str), here + ".net", "expected a net name")
        if item["net"] not in scoped_nets:
            continue
        _require(item["type"] in ITEM_TYPES, here + ".type",
                 "unsupported native item type in the checked USB nets",
                 "unsupported_scoped_item_type")
        for field in ("start", "end"):
            _vector(item.get(field), 2, here + "." + field)
        _strings(item.get("layers"), here + ".layers", nonempty=True)
        _strings(item.get("neighbors"), here + ".neighbors")
        _number(item.get("length"), here + ".length", 0)
        if item["type"] == "PAD":
            for field in ("ref", "number"):
                _text(item.get(field), here + "." + field)
            _vector(item.get("size"), 2, here + ".size")
            _vector(item.get("box"), 4, here + ".box")
            _require(all(value > 0 for value in item["size"]), here + ".size",
                     "pad dimensions must be positive")
            bounds = item["box"]
            _require(bounds[0] <= bounds[2] and bounds[1] <= bounds[3], here + ".box",
                     "pad bounds must be ordered")
            _number(item.get("angle"), here + ".angle")
            _strings(item.get("native_component_pad_ids"), here + ".native_component_pad_ids")
        else:
            _number(item.get("width"), here + ".width", 0)
            _require(item["width"] > 0, here + ".width", "copper width must be positive")
            if item["type"] == "PCB_VIA":
                _number(item.get("drill"), here + ".drill", 0)
                _require(0 < item["drill"] < item["width"], here + ".drill",
                         "via drill must be positive and smaller than its diameter")
            if item["type"] == "PCB_ARC":
                _vector(item.get("center"), 2, here + ".center")
                _vector(item.get("mid"), 2, here + ".mid")


def _native_component(anchor, items):
    """Return a same-net neighbor component, without inventing geometric joins."""
    adjacency = defaultdict(set)
    for uid, item in items.items():
        if item["net"] != anchor["net"]:
            continue
        for other in item.get("neighbors", []):
            if other in items and items[other]["net"] == anchor["net"]:
                adjacency[uid].add(other)
                adjacency[other].add(uid)
    seen = {anchor["id"]}
    pending = deque(seen)
    while pending:
        for other in adjacency[pending.popleft()] - seen:
            seen.add(other)
            pending.append(other)
    return seen


def _result(data, errors, proofs, routed_count=0):
    return {
        "status": "failed" if errors else "passed",
        "scope": SCOPE,
        "candidate_sha256": data.get("source_sha256") if isinstance(data, dict) else None,
        "blocking_findings": errors,
        "path_proofs": proofs,
        "reviewed_routed_objects_in_multi_terminal_nets": routed_count,
    }


def check(data, spec):
    """Check strict two-pad paths and exact selections of multi-terminal nets.

    A declared branch is an exact reviewed set of objects, not permission for
    arbitrary extra copper. Both its native pad component and its connection
    to every declared routed object must remain intact.
    """
    try:
        scoped_nets = _validate_contract(spec)
        _validate_data(data, scoped_nets)
    except _SchemaError as error:
        return _result(data, [error.finding], [])

    errors = []
    items = {item["id"]: item for item in data["items"]}
    multi_nets = set(spec["full_native_pad_sets"])
    routed = {uid for uid, item in items.items()
              if item["net"] in multi_nets and item["type"] in ROUTED_TYPES}
    for net, expected in spec["full_native_pad_sets"].items():
        actual = sorted(item["ref"] + "." + item["number"] for item in items.values()
                        if item["net"] == net and item["type"] == "PAD")
        if actual != sorted(expected):
            errors.append({"kind": "full_native_pad_set", "net": net,
                           "expected": sorted(expected), "actual": actual})

    covered = set()
    for case in spec["selected_cases"]:
        selected_nets = {net for path in case["signal_paths"]
                         for nets in path["nets"].values() for net in nets}
        for uid in case["include_native_item_uuids"]:
            item = items.get(uid)
            if item is None:
                errors.append({"kind": "missing_selected_item", "selection": case["name"],
                               "uuid": uid})
            elif item["net"] not in selected_nets:
                errors.append({"kind": "wrong_selection_net", "selection": case["name"],
                               "uuid": uid, "net": item["net"]})
            elif item["type"] in ROUTED_TYPES:
                covered.add(uid)

    expected_geometry = spec["expected_native_geometry"]
    for uid, expected in expected_geometry.items():
        if uid not in items:
            errors.append({"kind": "missing_expected_item", "uuid": uid})
        elif geometry(items[uid]) != expected:
            errors.append({"kind": "changed_reviewed_geometry", "uuid": uid})
    for uid, item in items.items():
        if item["net"] in multi_nets and uid not in expected_geometry:
            errors.append({"kind": "unreviewed_scoped_item", "uuid": uid})

    for branch in spec["declared_intentional_branches"]:
        ids = set(branch["routed_item_uuids"])
        covered.update(ids)
        for uid in ids:
            item = items.get(uid)
            if item is not None and (item["net"] != branch["net"] or
                                     item["type"] not in ROUTED_TYPES):
                errors.append({"kind": "wrong_branch_item", "branch": branch["name"],
                               "uuid": uid})
        anchor = items.get(branch["anchor_pad_uuid"])
        if (anchor is None or anchor["type"] != "PAD" or anchor["net"] != branch["net"] or
                anchor["ref"] + "." + anchor["number"] != branch["anchor_pad"]):
            errors.append({"kind": "invalid_branch_anchor", "branch": branch["name"]})
            continue
        component_ids = set(anchor["native_component_pad_ids"]) | {anchor["id"]}
        invalid = [uid for uid in component_ids if uid not in items or
                   items[uid]["type"] != "PAD" or items[uid]["net"] != branch["net"]]
        if invalid:
            errors.append({"kind": "invalid_native_pad_component", "branch": branch["name"],
                           "uuids": sorted(invalid)})
        else:
            actual = sorted(items[uid]["ref"] + "." + items[uid]["number"]
                            for uid in component_ids)
            expected = sorted(branch["expected_native_pad_component"])
            if actual != expected:
                errors.append({"kind": "branch_native_pad_component", "branch": branch["name"],
                               "expected": expected, "actual": actual})
        disconnected = ids - _native_component(anchor, items)
        if disconnected:
            errors.append({"kind": "branch_native_disconnected", "branch": branch["name"],
                           "uuids": sorted(disconnected)})

    if routed - covered:
        errors.append({"kind": "unexpected_uncovered_routed_objects", "uuids": sorted(routed - covered)})
    if covered - routed:
        errors.append({"kind": "missing_declared_routed_objects", "uuids": sorted(covered - routed)})
    if errors:
        return _result(data, errors, [], len(routed))

    proofs = []
    selections = [("direct two-pad paths", data, spec["direct_signal_paths"])]
    for case in spec["selected_cases"]:
        ids = set(case["include_native_item_uuids"])
        selected = dict(data, items=[item for item in data["items"] if item["id"] in ids])
        selections.append((case["name"], selected, case["signal_paths"]))
    for name, selected, definitions in selections:
        if not definitions:
            continue
        try:
            proof = check_paths(selected, definitions)
        except (AssertionError, KeyError, TypeError, ValueError, ZeroDivisionError) as error:
            errors.append({"kind": "path_check_error", "selection": name, "message": str(error)})
            continue
        proof["selection_name"] = name
        proofs.append(proof)
        errors.extend(dict(selection=name, **finding) for finding in proof["blocking_findings"])
    return _result(data, errors, proofs, len(routed))
