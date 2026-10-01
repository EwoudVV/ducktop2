"""Local USB path contracts reject unreviewed copper and broken branches."""

import copy
import math
import unittest

from center_usb_paths import SCOPE, check, geometry


def fixture():
    items = []
    endpoints = {}
    pad_sets = {}
    branches = []
    selected = []
    for polarity, y, source_number, end_number, branch_number in (
            ("P", 0.0, "1", "1", "3"), ("N", 5.0, "2", "2", "4")):
        net = "/USB_D" + polarity
        prefix = polarity.lower()
        source_id = prefix + "-source"
        end_id = prefix + "-end"
        branch_pad_id = prefix + "-branch-pad"
        main_id = prefix + "-main"
        branch_id = prefix + "-branch"
        pad_ids = [source_id, end_id, branch_pad_id]
        pads = [
            (source_id, "J1", source_number, [0.0, y], main_id),
            (end_id, "U1", end_number, [10.0, y], main_id),
            (branch_pad_id, "U1", branch_number, [5.0, y + 2], branch_id),
        ]
        for uid, ref, number, at, neighbor in pads:
            items.append({
                "id": uid, "type": "PAD", "net": net, "ref": ref, "number": number,
                "start": at[:], "end": at[:], "size": [0.4, 0.4], "angle": 0.0,
                "box": [at[0] - .2, at[1] - .2, at[0] + .2, at[1] + .2],
                "layers": ["F.Cu"], "length": 0.0, "neighbors": [neighbor],
                "native_component_pad_ids": pad_ids[:],
            })
        for uid, start, end, neighbors in (
                (main_id, [0.0, y], [10.0, y], [source_id, end_id, branch_id]),
                (branch_id, [5.0, y], [5.0, y + 2], [main_id, branch_pad_id])):
            items.append({
                "id": uid, "type": "PCB_TRACK", "net": net,
                "start": start, "end": end, "width": .2, "layers": ["F.Cu"],
                "length": math.dist(start, end), "neighbors": neighbors,
            })
        endpoints[net] = ["J1." + source_number, "U1." + end_number]
        pad_sets[net] = sorted(endpoints[net] + ["U1." + branch_number])
        branches.append({
            "name": polarity + " duplicate protection pad",
            "net": net, "anchor_pad_uuid": branch_pad_id,
            "anchor_pad": "U1." + branch_number,
            "expected_native_pad_component": pad_sets[net],
            "routed_item_uuids": [branch_id],
        })
        selected.extend([source_id, end_id, main_id])
    path = {
        "name": "connector to far protection pads",
        "nets": {"P": ["/USB_DP"], "N": ["/USB_DN"]},
        "endpoints": endpoints, "max_pn_difference_mm": .1, "via_transition_count": 0,
    }
    data = {"source_sha256": "native-fixture", "items": items}
    spec = {
        "schema_version": 1, "direct_signal_paths": [],
        "selected_cases": [{"name": "local connector path", "signal_paths": [path],
                            "include_native_item_uuids": selected}],
        "full_native_pad_sets": pad_sets,
        "expected_native_geometry": {item["id"]: geometry(item) for item in items},
        "declared_intentional_branches": branches,
    }
    return data, spec


class UsbPathTests(unittest.TestCase):
    def setUp(self):
        self.data, self.spec = fixture()

    def item(self, uid):
        return next(item for item in self.data["items"] if item["id"] == uid)

    def assert_failed_with(self, kind):
        result = check(self.data, self.spec)
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["scope"], SCOPE)
        self.assertIn(kind, {finding["kind"] for finding in result["blocking_findings"]})
        return result

    def test_valid_selections_and_exact_branches(self):
        before_data, before_spec = copy.deepcopy(self.data), copy.deepcopy(self.spec)
        result = check(self.data, self.spec)
        self.assertEqual(result["status"], "passed")
        self.assertEqual(result["scope"], "local USB paths and connector branches")
        self.assertEqual(result["reviewed_routed_objects_in_multi_terminal_nets"], 4)
        self.assertEqual(len(result["path_proofs"]), 1)
        self.assertEqual(self.data, before_data)
        self.assertEqual(self.spec, before_spec)

    def test_uncovered_new_spur_is_rejected(self):
        spur = copy.deepcopy(self.item("p-main"))
        spur.update(id="new-spur", start=[6.0, 0.0], end=[6.0, 1.0], length=1.0,
                    neighbors=["p-main"])
        self.data["items"].append(spur)
        self.item("p-main")["neighbors"].append("new-spur")
        self.assert_failed_with("unexpected_uncovered_routed_objects")

    def test_modified_declared_branch_is_rejected(self):
        self.item("p-branch")["end"][1] += .25
        self.assert_failed_with("changed_reviewed_geometry")

    def test_geometry_copy_does_not_alias_native_coordinates(self):
        saved = geometry(self.item("p-branch"))
        self.item("p-branch")["start"][0] += 1
        self.assertEqual(saved["start"], [5.0, 0.0])

    def test_changed_pad_is_rejected(self):
        self.item("p-branch-pad")["number"] = "99"
        self.assert_failed_with("full_native_pad_set")

    def test_missing_pad_is_rejected_without_crashing(self):
        self.data["items"] = [item for item in self.data["items"] if item["id"] != "p-branch-pad"]
        self.assert_failed_with("full_native_pad_set")

    def test_native_disconnected_branch_component_is_rejected(self):
        self.item("p-branch-pad")["native_component_pad_ids"] = ["p-branch-pad"]
        self.assert_failed_with("branch_native_pad_component")

    def test_disconnected_branch_copper_cannot_hide_behind_its_anchor(self):
        # Leave the anchor's component claim intact, but remove all actual
        # native contacts to the declared branch track.
        self.item("p-branch")["neighbors"] = []
        for item in self.data["items"]:
            item["neighbors"] = [uid for uid in item["neighbors"] if uid != "p-branch"]
        self.assert_failed_with("branch_native_disconnected")

    def test_duplicate_native_id_is_rejected(self):
        self.data["items"].append(copy.deepcopy(self.item("p-main")))
        self.assert_failed_with("duplicate_native_id")

    def test_unknown_scoped_native_type_is_rejected(self):
        self.data["items"].append({"id": "copper-shape", "type": "PCB_SHAPE", "net": "/USB_DP"})
        self.assert_failed_with("unsupported_scoped_item_type")

    def test_unrelated_native_shapes_do_not_expand_the_scope(self):
        self.data["items"].append({"id": "other-shape", "type": "PCB_SHAPE", "net": "/OTHER"})
        self.assertEqual(check(self.data, self.spec)["status"], "passed")

    def test_selection_cannot_claim_another_net_as_covered(self):
        self.data["items"].append({"id": "other-shape", "type": "PCB_SHAPE", "net": "/OTHER"})
        self.spec["selected_cases"][0]["include_native_item_uuids"].append("other-shape")
        self.assert_failed_with("wrong_selection_net")

    def test_branch_cannot_be_silently_added_to_a_strict_selected_path(self):
        self.spec["selected_cases"][0]["include_native_item_uuids"].append("p-branch")
        self.assert_failed_with("free_branch_or_stub")

    def test_invalid_contract_schema_fails_closed(self):
        mutations = [
            lambda spec: spec.update(schema_version=True),
            lambda spec: spec["selected_cases"][0].update(include_native_item_uuids="p-main"),
            lambda spec: spec["selected_cases"][0]["signal_paths"][0].update(max_pn_difference_mm=float("nan")),
            lambda spec: spec["selected_cases"][0]["signal_paths"][0].update(via_transition_count=True),
            lambda spec: spec["expected_native_geometry"]["p-branch"].update(net=[]),
            lambda spec: spec["declared_intentional_branches"][0].update(net=[]),
        ]
        for mutate in mutations:
            with self.subTest(mutate=mutate):
                self.data, self.spec = fixture()
                mutate(self.spec)
                self.assert_failed_with("schema_error")

    def test_direct_two_pad_paths_remain_strict(self):
        path = copy.deepcopy(self.spec["selected_cases"][0]["signal_paths"][0])
        keep = set(self.spec["selected_cases"][0]["include_native_item_uuids"])
        self.data["items"] = [item for item in self.data["items"] if item["id"] in keep]
        for item in self.data["items"]:
            item["neighbors"] = [uid for uid in item["neighbors"] if uid in keep]
            if item["type"] == "PAD":
                item["native_component_pad_ids"] = [uid for uid in item["native_component_pad_ids"] if uid in keep]
        self.spec = {"schema_version": 1, "direct_signal_paths": [path], "selected_cases": [],
                     "full_native_pad_sets": {}, "expected_native_geometry": {},
                     "declared_intentional_branches": []}
        self.assertEqual(check(self.data, self.spec)["status"], "passed")
        spur = copy.deepcopy(self.item("p-main"))
        spur.update(id="direct-spur", start=[6.0, 0.0], end=[6.0, 1.0], length=1.0, neighbors=[])
        self.data["items"].append(spur)
        self.assert_failed_with("free_branch_or_stub")


if __name__ == "__main__":
    unittest.main()
