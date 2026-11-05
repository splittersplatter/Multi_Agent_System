# Historical epistemic API reference

Source/tests were deleted. Names below describe the former baseline, not current
implementations or committed future signatures. Use as design references for
Stages 00/02; implement and revalidate when requested. [Survey](election-manipulation-literature-survey.md).

The supplied reference is Bakhtiari, van Ditmarsch, and Saffidine,
“How does uncertainty about other voters determine a strategic vote?”
(arXiv:1809.10489v2, 2019). Historical concept/API mapping:

| Paper concept | Former API names; currently absent |
| --- | --- |
| Preference, profile, plurality rule | `strategic.all_preferences`, `normalize_profile`, `winner_for_profile` |
| Manipulation (Definition 2) | `manipulation`, `manipulations` |
| Game-theoretic dominant preference (Definition 3) | `dominant_preferences` |
| Equilibrium profile (Definition 4) | `equilibrium` |
| Knowledge profile (Definition 5) | `World`, `EpistemicModel` / `KnowledgeProfile` |
| Knowledge and uncertainty (Definition 6) | `knows`, `considers_possible`, `uncertain_about` |
| De dicto / de re manipulation (Definition 8) | `de_dicto_manipulation`, `de_re_manipulations` |
| Dominant manipulation (Definition 10) | `dominant_manipulations` |
| Pessimistic manipulation (Definition 12) | `pessimistic_manipulations` |
| Conditional equilibrium (Definition 13) | `conditional_equilibrium` |
| Public announcement update (Definition 15) | `EpistemicModel.update`, `public_announcement` |
| Updated conditional profile (Definition 18) | `update_conditional_profile` |
| Logic of knowledge and voting (Definitions 22–23) | `logic.ProfileIs`, `PreferenceIs`, `Prefers`, `WinnerIs`, `Knows`, `After` |

Reference assumptions: strict ordinal rankings, deterministic plurality ties,
finite pure strategies/knowledge profiles. No current implementation exists.
Complete proof systems, private/lying announcements, probabilistic beliefs,
non-plurality rules and mixed strategies are not implied by this mapping.
