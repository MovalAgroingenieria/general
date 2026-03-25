# 2026 Moval Agroingeniería
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

"""Paquete de regresión: los 9 puntos obligatorios de QA frente a la especificación funcional.

Cada test es autónomo, determinista y con fixtures mínimas. HTTP asistencia: ``test_http_attendance``.
"""

from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase

from .common import AssemblyTestMixin
from .http_common import AssemblyHttpCase


class TestFunctionalSpecCompliancePack(AssemblyTestMixin, TransactionCase):
    """QA 1–8 (modelos y lógica de negocio)."""

    def test_qa_01_quorum_counts_people_not_vote_weights(self):
        """Quorum: personas distintas; pesos ``partner.vote`` no influyen al conteo."""
        assembly, _partners = self._assembly_four_partners()
        vote_type = assembly.assembly_type_id.vote_type_ids[0]
        att0, att1 = assembly.attendee_ids[0], assembly.attendee_ids[1]
        self._give_partner_votes(att0.partner_id, vote_type, 500)
        self._give_partner_votes(att1.partner_id, vote_type, 1)
        att0.action_confirm()
        att1.action_confirm()
        assembly.invalidate_recordset()
        self.assertEqual(assembly.total_present_attendees, 2)
        self.assertEqual(len(assembly._get_present_partner_ids()), 2)

    def _assembly_four_partners(self):
        partners = self._create_partners(self.env, 4, prefix="PackQ")
        domain = "[('id', 'in', %s)]" % partners.ids
        assembly, _ = self._create_assembly_with_agenda(partner_domain=domain)
        assembly.action_generate_attendees()
        return assembly, partners

    def test_qa_02_non_attendee_delegator_transfers_via_partner_vote_only(self):
        """Delegador sin fila de asistente: votos vía ``partner.vote`` al delegado; sin filas del delegador."""
        env = self.env
        p_del = env["res.partner"].create(
            {"name": "PackExtDel", "is_company": False, "assembly_excluded": True}
        )
        p_def = env["res.partner"].create(
            {"name": "PackDelegate", "is_company": False, "assembly_excluded": False}
        )
        domain = "[('id', 'in', %s)]" % ([p_del.id, p_def.id],)
        assembly, _ = self._create_assembly_with_agenda(partner_domain=domain)
        assembly.action_generate_attendees()
        self.assertFalse(
            assembly.attendee_ids.filtered(lambda a: a.partner_id == p_del)
        )
        vote_type = assembly.assembly_type_id.vote_type_ids[0]
        self._give_partner_votes(p_del, vote_type, 7)
        self._give_partner_votes(p_def, vote_type, 2)
        delegate_att = assembly.attendee_ids.filtered(lambda a: a.partner_id == p_def)
        delegate_att.action_confirm()
        env["assembly.delegation"].create(
            {
                "assembly_id": assembly.id,
                "partner_id": p_del.id,
                "delegate_partner_id": p_def.id,
                "vote_type_ids": [(6, 0, vote_type.ids)],
                "delegation_state": "confirmed",
            }
        )
        delegate_att.recompute_attendee_vote_lines()
        Av = env["assembly.attendee.vote"]
        self.assertFalse(
            Av.search(
                [
                    ("attendee_id.assembly_id", "=", assembly.id),
                    ("attendee_id.partner_id", "=", p_del.id),
                ]
            )
        )
        line_b = Av.search(
            [
                ("attendee_id", "=", delegate_att.id),
                ("vote_type_id", "=", vote_type.id),
            ],
            limit=1,
        )
        self.assertTrue(line_b)
        self.assertEqual(line_b.delegated_in_votes, 7.0)
        self.assertEqual(line_b.own_votes, 2.0)

    def _assembly_two_vote_types_pack(self):
        env = self.env
        vt1 = self._create_vote_type(env, name="Pack VT1")
        vt2 = self._create_vote_type(env, name="Pack VT2")
        atype = self._create_assembly_type(env, name="Pack type 2vt", vote_type=vt1)
        atype.write({"vote_type_ids": [(4, vt2.id)]})
        partners = self._create_partners(env, 3, prefix="Pack2VT")
        assembly, _ = self._create_assembly_with_agenda(
            assembly_type=atype,
            partner_domain="[('id', 'in', %s)]" % partners.ids,
        )
        assembly.vote_type_ids = [(6, 0, [vt1.id, vt2.id])]
        assembly.action_generate_attendees()
        return assembly, vt1, vt2

    def test_qa_03_partial_delegation_only_selected_vote_types_transfer(self):
        """Delegación parcial: solo los tipos enlazados transfieren in/out."""
        env = self.env
        assembly, vt1, vt2 = self._assembly_two_vote_types_pack()
        a, b = assembly.attendee_ids[0], assembly.attendee_ids[1]
        self._give_partner_votes(a.partner_id, vt1, 4)
        self._give_partner_votes(a.partner_id, vt2, 3)
        self._give_partner_votes(b.partner_id, vt1, 1)
        self._give_partner_votes(b.partner_id, vt2, 2)
        (a | b).action_confirm()
        env["assembly.delegation"].create(
            {
                "assembly_id": assembly.id,
                "partner_id": a.partner_id.id,
                "delegate_partner_id": b.partner_id.id,
                "vote_type_ids": [(6, 0, [vt1.id])],
                "delegation_state": "confirmed",
            }
        )
        assembly.attendee_ids.recompute_attendee_vote_lines()
        Av = env["assembly.attendee.vote"]
        la2 = Av.search(
            [("attendee_id", "=", a.id), ("vote_type_id", "=", vt2.id)], limit=1
        )
        lb2 = Av.search(
            [("attendee_id", "=", b.id), ("vote_type_id", "=", vt2.id)], limit=1
        )
        self.assertEqual(la2.delegated_out_votes, 0.0)
        self.assertEqual(lb2.delegated_in_votes, 0.0)
        self.assertEqual(lb2.own_votes, 2.0)

    def test_qa_04_full_delegation_empty_m2m_all_assembly_vote_types_transfer(self):
        """Delegación total: M2M vacío equivale a todos los tipos de la asamblea."""
        env = self.env
        assembly, vt1, vt2 = self._assembly_two_vote_types_pack()
        a, b = assembly.attendee_ids[0], assembly.attendee_ids[1]
        self._give_partner_votes(a.partner_id, vt1, 2)
        self._give_partner_votes(a.partner_id, vt2, 3)
        self._give_partner_votes(b.partner_id, vt1, 1)
        self._give_partner_votes(b.partner_id, vt2, 1)
        (a | b).action_confirm()
        env["assembly.delegation"].create(
            {
                "assembly_id": assembly.id,
                "partner_id": a.partner_id.id,
                "delegate_partner_id": b.partner_id.id,
                "vote_type_ids": [(5, 0, 0)],
                "delegation_state": "confirmed",
            }
        )
        assembly.attendee_ids.recompute_attendee_vote_lines()
        Av = env["assembly.attendee.vote"]
        for vt, out_a, in_b in ((vt1, 2.0, 2.0), (vt2, 3.0, 3.0)):
            la = Av.search(
                [("attendee_id", "=", a.id), ("vote_type_id", "=", vt.id)], limit=1
            )
            lb = Av.search(
                [("attendee_id", "=", b.id), ("vote_type_id", "=", vt.id)], limit=1
            )
            self.assertEqual(la.delegated_out_votes, out_a)
            self.assertEqual(lb.delegated_in_votes, in_b)

    def test_qa_05_delegate_must_be_confirmed_for_vote_effect(self):
        """Sin delegado confirmado no hay efecto de voto pese a delegación confirmada."""
        assembly, _p = self._assembly_four_partners()
        vote_type = assembly.assembly_type_id.vote_type_ids[0]
        delegator = assembly.attendee_ids[0]
        delegate = assembly.attendee_ids[1]
        self._give_partner_votes(delegator.partner_id, vote_type, 9)
        self._give_partner_votes(delegate.partner_id, vote_type, 1)
        (delegator | delegate).action_confirm()
        self.env["assembly.delegation"].create(
            {
                "assembly_id": assembly.id,
                "partner_id": delegator.partner_id.id,
                "delegate_partner_id": delegate.partner_id.id,
                "vote_type_ids": [(6, 0, vote_type.ids)],
                "delegation_state": "confirmed",
            }
        )
        assembly.attendee_ids.recompute_attendee_vote_lines()
        Av = self.env["assembly.attendee.vote"]
        line_b = Av.search(
            [
                ("attendee_id", "=", delegate.id),
                ("vote_type_id", "=", vote_type.id),
            ],
            limit=1,
        )
        self.assertEqual(line_b.delegated_in_votes, 9.0)
        delegate.action_mark_absent()
        line_b = Av.search(
            [
                ("attendee_id", "=", delegate.id),
                ("vote_type_id", "=", vote_type.id),
            ],
            limit=1,
        )
        self.assertEqual(line_b.delegated_in_votes, 0.0)

    def test_qa_06_no_chained_delegation_same_vote_type(self):
        """No hay cadena: B recibe tipo T de A → B no puede delegar T a C."""
        env = self.env
        vt1 = self._create_vote_type(env, name="Pack Chain VT1")
        vt2 = self._create_vote_type(env, name="Pack Chain VT2")
        atype = self._create_assembly_type(env, name="Pack chain type", vote_type=vt1)
        atype.write({"vote_type_ids": [(4, vt2.id)]})
        partners = self._create_partners(env, 3, prefix="PackChain")
        assembly, _ = self._create_assembly_with_agenda(
            assembly_type=atype,
            partner_domain="[('id', 'in', %s)]" % partners.ids,
        )
        assembly.vote_type_ids = [(6, 0, [vt1.id, vt2.id])]
        assembly.action_generate_attendees()
        a_att, b_att, c_att = assembly.attendee_ids.sorted("id")
        for att in (a_att, b_att, c_att):
            self._give_partner_votes(att.partner_id, vt1, 5)
            self._give_partner_votes(att.partner_id, vt2, 5)
        (a_att | b_att | c_att).action_confirm()
        Delegation = env["assembly.delegation"]
        Delegation.create(
            {
                "assembly_id": assembly.id,
                "partner_id": a_att.partner_id.id,
                "delegate_partner_id": b_att.partner_id.id,
                "vote_type_ids": [(6, 0, [vt1.id])],
                "delegation_state": "confirmed",
            }
        )
        with self.assertRaises(ValidationError):
            Delegation.create(
                {
                    "assembly_id": assembly.id,
                    "partner_id": b_att.partner_id.id,
                    "delegate_partner_id": c_att.partner_id.id,
                    "vote_type_ids": [(6, 0, [vt1.id])],
                    "delegation_state": "confirmed",
                }
            )

    def test_qa_07_attendee_vote_rows_unique_across_recomputes(self):
        """Tras varios recomputos: exactamente una fila por (asistente, tipo) en extremos."""
        assembly, _ = self._create_assembly_with_agenda()
        assembly.action_generate_attendees()
        vt = assembly.assembly_type_id.vote_type_ids[0]
        a, b = assembly.attendee_ids[0], assembly.attendee_ids[1]
        self._give_partner_votes(a.partner_id, vt, 6)
        self._give_partner_votes(b.partner_id, vt, 2)
        (a | b).action_confirm()
        self.env["assembly.delegation"].create(
            {
                "assembly_id": assembly.id,
                "partner_id": a.partner_id.id,
                "delegate_partner_id": b.partner_id.id,
                "vote_type_ids": [(6, 0, vt.ids)],
                "delegation_state": "confirmed",
            }
        )
        Av = self.env["assembly.attendee.vote"]
        for _ in range(6):
            assembly.attendee_ids.recompute_attendee_vote_lines()
        self.assertEqual(
            Av.search_count(
                [
                    ("attendee_id", "in", (a | b).ids),
                    ("vote_type_id", "=", vt.id),
                ]
            ),
            2,
        )

    def test_qa_08_state_transition_helpers_enforce_spec(self):
        """Grafo de estados: asamblea (p. ej. closed→cancelled) y asistente (sin confirmed→registered)."""
        Asm = self.env["assembly.assembly"]
        self.assertTrue(
            Asm._assembly_is_allowed_state_transition("closed", "cancelled")
        )
        self.assertFalse(Asm._assembly_is_allowed_state_transition("draft", "open"))
        Att = self.env["assembly.attendee"]
        self.assertFalse(
            Att._attendee_is_allowed_registration_state_transition(
                "confirmed", "registered"
            )
        )
        self.assertTrue(
            Att._attendee_is_allowed_registration_state_transition(
                "confirmed", "absent"
            )
        )


class TestFunctionalSpecCompliancePackHttp(AssemblyHttpCase):
    """QA 9: contrato HTTP del controlador de asistencia (requiere servidor HTTP)."""

    def test_qa_09_manager_valid_deep_link_redirects(self):
        """Manager en asamblea abierta: 302 hacia formulario de asistente."""
        self.assembly.action_announce()
        self.assembly.action_open_registration()
        self.authenticate(self.user_manager.login, "assembly_manager_http")
        url = "/assembly/attendance?assembly_id=%s&participant_id=%s" % (
            self.assembly.id,
            self.attendee.partner_id.id,
        )
        res = self.url_open(url, allow_redirects=False)
        self.assertIn(res.status_code, (302, 303))
        location = res.headers.get("Location", "")
        self.assertTrue(
            "assembly.attendee" in location or "id=%s" % self.attendee.id in location,
        )

    def test_qa_09b_missing_query_params_plain_text_400(self):
        """Parámetros faltantes: 400 y cuerpo descriptivo (spec)."""
        self.authenticate("admin", "admin")
        res = self.url_open("/assembly/attendance", allow_redirects=False)
        self.assertEqual(res.status_code, 400)
        low = res.content.lower()
        self.assertTrue(b"assembly_id" in low or b"participant" in low)
