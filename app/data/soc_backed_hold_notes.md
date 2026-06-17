# SOC-backed HOLD scoring

This radar keeps APPLY strict.

A role may enter HOLD even when salary or explicit role-level sponsorship language is unclear if all of the following are true:

1. The job is from an official ATS or company source.
2. The employer is matched to the sponsor register.
3. The role is UK-based or UK-unclear, not clearly non-UK.
4. The title or description maps to one of Karan Dhar's realistic sponsored role families.
5. The employer has a configured role-family/SOC signal in `app/scoring.py`.
6. There is no hard anti-sponsorship language and salary is not clearly below threshold.

This should be treated as:

`SOC-backed HOLD — manual sponsorship check required`

It is not an APPLY decision. It exists to surface roles worth checking manually where employer/SOC pattern makes the lead more plausible than a generic watchlist role.
