import copy
import unittest

try:
    from jev_lab import adapters, engine, provider
except ImportError:
    adapters = None


def gateway_like(request, *, confidence=True, omit_output_tokens=False, wire_type=None):
    """Authored to the documented AI SDK 7 evaluation shape. NOT a captured response.

    Mirrors what the Vercel AI SDK documents: answers preserve question IDs,
    Choice and Score answers carry no distribution, the yes/no primitive is
    named ``boolean``, and TypeSafe confidence arrives through provider metadata.
    """
    answers, meta = {}, {}
    for qid, q in request["questions"].items():
        if q["type"] == "choice":
            answers[qid] = {
                "type": wire_type or "choice",
                "choice": min(q["criteria"]),
            }
        elif q["type"] == "score":
            answers[qid] = {"type": wire_type or "score", "score": 1.0}
        else:
            answers[qid] = {"type": wire_type or "boolean", "probability": 0.02}
        if confidence:
            meta[qid] = 0.9
    usage = {"input_tokens": 120}
    if not omit_output_tokens:
        usage["output_tokens"] = 8
    response = {"model": "typesafe-ai/jev", "answers": answers, "usage": usage}
    if confidence:
        response["providerMetadata"] = {"typesafe": {"confidence": meta}}
    return response


@unittest.skipIf(adapters is None, "adapter interface pending")
class InterfaceTests(unittest.TestCase):
    def test_registry_exposes_three_arms(self):
        for name in ("replay", "native", "gateway"):
            self.assertEqual(adapters.build(name).name, name)

    def test_unknown_arm_is_rejected(self):
        with self.assertRaises(ValueError):
            adapters.build("unregistered-provider")

    def test_every_arm_reports_the_two_tracks(self):
        for name in ("replay", "native", "gateway"):
            arm = adapters.build(name)
            self.assertEqual(
                set(arm.tracks), {"minimal_decision", "comparable_distribution"}
            )
            self.assertFalse(
                arm.live_verified, "no route has been checked against a live provider"
            )

    def test_call_returns_raw_provenance_and_normalized(self):
        request = engine.request_for(engine.case_by_id("S02"))
        result = adapters.build("replay").call(request, "S02")
        self.assertEqual(set(result), {"raw", "provenance", "normalized"})
        self.assertEqual(result["provenance"]["kind"], "synthetic_replay")
        self.assertEqual(
            result["normalized"]["schema_version"], adapters.SCHEMA_VERSION
        )


@unittest.skipIf(adapters is None, "adapter interface pending")
class NativeNormalizationTests(unittest.TestCase):
    def setUp(self):
        self.case = engine.case_by_id("S02")
        self.request = engine.request_for(self.case)
        self.native = provider.replay("S02")
        self.normalized = adapters.normalize_native(self.request, self.native)

    def test_choice_answers_keep_the_category_and_a_real_distribution(self):
        owner = self.normalized["records"]["owner"]
        self.assertEqual(owner["answer"], self.native["answers"]["owner"]["choice"])
        self.assertEqual(owner["wire_type"], "choice")
        self.assertEqual(owner["primitive"], "category")
        self.assertEqual(owner["distribution"]["kind"], "categorical")
        self.assertEqual(
            owner["distribution"]["probabilities"],
            self.native["answers"]["owner"]["probabilities"],
        )

    def test_provider_confidence_is_preserved_but_not_a_class_probability(self):
        owner = self.normalized["records"]["owner"]
        self.assertEqual(
            owner["provider_confidence"]["value"],
            self.native["answers"]["owner"]["confidence"],
        )
        self.assertNotIn(
            owner["provider_confidence"]["value"],
            owner["distribution"]["probabilities"].values(),
        )
        self.assertIn("not", owner["provider_confidence"]["interpretation"].lower())

    def test_score_answers_keep_a_weighted_index_and_its_distribution(self):
        severity = self.normalized["records"]["severity"]
        self.assertEqual(severity["primitive"], "ordered")
        self.assertEqual(severity["distribution"]["kind"], "ordinal")
        self.assertEqual(
            severity["answer"], self.native["answers"]["severity"]["score"]
        )

    def test_native_yes_no_normalizes_to_a_comparable_binary(self):
        sufficient = self.normalized["records"]["sufficient"]
        self.assertEqual(sufficient["wire_type"], "noul")
        self.assertEqual(sufficient["primitive"], "proposition")
        self.assertEqual(
            sufficient["answer"], self.native["answers"]["sufficient"]["noul"]
        )
        self.assertAlmostEqual(
            sufficient["distribution"]["probabilities"]["yes"],
            self.native["answers"]["sufficient"]["noul"],
        )

    def test_native_schema_drift_fails_closed(self):
        broken = copy.deepcopy(self.native)
        del broken["answers"]["sufficient"]["noul"]
        with self.assertRaises(ValueError):
            adapters.normalize_native(self.request, broken)

    def test_missing_native_distribution_is_not_fabricated(self):
        broken = copy.deepcopy(self.native)
        del broken["answers"]["owner"]["probabilities"]
        with self.assertRaises(ValueError):
            adapters.normalize_native(self.request, broken)


@unittest.skipIf(adapters is None, "adapter interface pending")
class GatewayNormalizationTests(unittest.TestCase):
    def setUp(self):
        self.case = engine.case_by_id("S02")
        self.request = engine.request_for(self.case)
        self.response = gateway_like(self.request)
        self.normalized = adapters.normalize_gateway(self.request, self.response)

    def test_boolean_replaces_noul_and_stays_comparable(self):
        sufficient = self.normalized["records"]["sufficient"]
        self.assertEqual(sufficient["wire_type"], "boolean")
        self.assertEqual(sufficient["primitive"], "proposition")
        self.assertEqual(sufficient["answer"], 0.02)
        self.assertEqual(sufficient["distribution"]["source"], "provider_boolean")
        self.assertAlmostEqual(sufficient["distribution"]["probabilities"]["no"], 0.98)

    def test_choice_has_no_distribution_and_says_so_instead_of_inventing_one(self):
        owner = self.normalized["records"]["owner"]
        self.assertEqual(owner["answer"], self.response["answers"]["owner"]["choice"])
        self.assertIsNone(owner["distribution"])
        self.assertIn("fabricat", owner["distribution_note"].lower())

    def test_score_has_no_distribution_either(self):
        severity = self.normalized["records"]["severity"]
        self.assertIsNone(severity["distribution"])
        self.assertIn("fabricat", severity["distribution_note"].lower())

    def test_typesafe_confidence_metadata_is_preserved_verbatim(self):
        owner = self.normalized["records"]["owner"]
        self.assertEqual(owner["provider_confidence"]["metric"], "typesafe_confidence")
        self.assertEqual(owner["provider_confidence"]["value"], 0.9)
        self.assertIsNone(owner["distribution"])
        self.assertIn("not", owner["provider_confidence"]["interpretation"].lower())

    def test_absent_confidence_metadata_is_none_not_zero(self):
        normalized = adapters.normalize_gateway(
            self.request, gateway_like(self.request, confidence=False)
        )
        self.assertIsNone(normalized["records"]["owner"]["provider_confidence"])

    def test_unknown_wire_type_fails_closed(self):
        with self.assertRaises(ValueError):
            adapters.normalize_gateway(
                self.request, gateway_like(self.request, wire_type="distribution")
            )

    def test_out_of_range_boolean_probability_fails_closed(self):
        response = gateway_like(self.request)
        response["answers"]["sufficient"]["probability"] = 1.4
        with self.assertRaises(ValueError):
            adapters.normalize_gateway(self.request, response)

    def test_choice_outside_declared_criteria_fails_closed(self):
        response = gateway_like(self.request)
        response["answers"]["owner"]["choice"] = "marketing"
        with self.assertRaises(ValueError):
            adapters.normalize_gateway(self.request, response)

    def test_question_id_drift_fails_closed(self):
        response = gateway_like(self.request)
        del response["answers"]["contradiction"]
        with self.assertRaises(ValueError):
            adapters.normalize_gateway(self.request, response)

    def test_missing_output_tokens_does_not_invent_a_count(self):
        response = gateway_like(self.request, omit_output_tokens=True)
        provenance = adapters.gateway_provenance(response, 12.0)
        self.assertIsNone(provenance["usage"].get("output_tokens"))
        self.assertFalse(provenance["usage"]["output_tokens_known"])

    def test_usage_cost_comes_from_input_tokens_only_when_output_is_unknown(self):
        response = gateway_like(self.request, omit_output_tokens=True)
        provenance = adapters.gateway_provenance(response, 12.0)
        self.assertAlmostEqual(
            provenance["estimated_cost_usd"],
            120 / 1_000_000 * adapters.GATEWAY_PRICE_PER_MILLION_INPUT,
        )


@unittest.skipIf(adapters is None, "adapter interface pending")
class GatewayTransportTests(unittest.TestCase):
    def test_gateway_fails_closed_without_an_approved_transport(self):
        request = engine.request_for(engine.case_by_id("S02"))
        arm = adapters.build("gateway")
        with self.assertRaises(PermissionError) as caught:
            arm.call(request, "S02")
        self.assertIn("nothing was sent", str(caught.exception).lower())

    def test_gateway_pins_the_documented_package_version(self):
        self.assertEqual(adapters.GATEWAY_PACKAGE_PIN, "ai@7.0.105")
        self.assertEqual(
            adapters.build("gateway").pinned_version, adapters.GATEWAY_PACKAGE_PIN
        )

    def test_injected_transport_is_normalized_the_same_way(self):
        request = engine.request_for(engine.case_by_id("S02"))
        seen = {}

        def transport(payload):
            seen["payload"] = payload
            return gateway_like(payload)

        arm = adapters.build("gateway", transport=transport)
        result = arm.call(request, "S02")
        self.assertEqual(seen["payload"]["model"], "typesafe-ai/jev")
        self.assertEqual(result["provenance"]["kind"], "live_gateway")
        self.assertEqual(result["provenance"]["model_calls"], 1)
        self.assertEqual(
            result["normalized"]["records"]["owner"]["wire_type"], "choice"
        )
