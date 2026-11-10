from decimal import Decimal

from apps.students.models import StudentProfile


def _normalized(value):
    return str(value).strip().casefold()


def _criterion_check(key, label, expected, actual, matches, missing_reason):
    if actual is None or actual == "":
        return {
            "key": key,
            "label": label,
            "status": "MISSING",
            "expected": expected,
            "actual": None,
            "reason": missing_reason,
        }
    return {
        "key": key,
        "label": label,
        "status": "MET" if matches else "NOT_MET",
        "expected": expected,
        "actual": str(actual),
        "reason": (
            f"{label} requirement is satisfied."
            if matches
            else f"{label} does not meet this opportunity's requirement."
        ),
    }


def evaluate_eligibility(opportunity, profile=None):
    """Compare the available student profile against every configured requirement."""
    criteria = opportunity.eligibility_criteria or {}
    checks = []
    missing_fields = []

    if profile is None:
        required_fields = []
        if "minimum_cgpa" in criteria:
            required_fields.append("CGPA")
        if "graduation_years" in criteria:
            required_fields.append("graduation year")
        if "degree_programmes" in criteria:
            required_fields.append("degree programme")
        if "departments" in criteria:
            required_fields.append("department")
        if opportunity.required_skills or criteria.get("required_skills"):
            required_fields.append("skills")
        return {
            "status": "INCOMPLETE_PROFILE",
            "eligible": None,
            "checks": [],
            "reasons": ["Create your student profile to check eligibility."],
            "missing_fields": ["student profile", *required_fields],
        }

    if "minimum_cgpa" in criteria:
        minimum = Decimal(str(criteria["minimum_cgpa"]))
        actual = profile.cgpa
        checks.append(
            _criterion_check(
                "cgpa",
                "CGPA",
                str(minimum),
                actual,
                actual is not None and actual >= minimum,
                "Add your current CGPA to your student profile.",
            )
        )

    if "graduation_years" in criteria:
        allowed = criteria["graduation_years"]
        actual = profile.graduation_year
        checks.append(
            _criterion_check(
                "graduation_year",
                "Graduation year",
                ", ".join(str(year) for year in allowed),
                actual,
                actual in allowed,
                "Add your expected graduation year to your student profile.",
            )
        )

    if "degree_programmes" in criteria:
        allowed = criteria["degree_programmes"]
        actual = profile.degree_programme
        matches = any(_normalized(actual) == _normalized(value) for value in allowed)
        checks.append(
            _criterion_check(
                "degree_programme",
                "Degree programme",
                ", ".join(allowed),
                actual,
                matches,
                "Add your degree programme to your student profile.",
            )
        )

    if "departments" in criteria:
        allowed = criteria["departments"]
        actual = profile.department
        matches = any(_normalized(actual) == _normalized(value) for value in allowed)
        checks.append(
            _criterion_check(
                "department",
                "Department",
                ", ".join(allowed),
                actual,
                matches,
                "Add your academic department to your student profile.",
            )
        )

    required_skills = list(opportunity.required_skills or [])
    required_skills.extend(criteria.get("required_skills", []))
    required_skills = list(dict.fromkeys(_normalized(skill) for skill in required_skills))
    if required_skills:
        actual_skill_list = profile.skills or []
        actual_skills = {_normalized(skill) for skill in actual_skill_list}
        missing_skills = [skill for skill in required_skills if skill not in actual_skills]
        skill_status = (
            "MISSING"
            if not actual_skill_list
            else "MET"
            if not missing_skills
            else "NOT_MET"
        )
        checks.append(
            {
                "key": "skills",
                "label": "Required skills",
                "status": skill_status,
                "expected": ", ".join(required_skills),
                "actual": ", ".join(actual_skill_list) if actual_skill_list else None,
                "reason": (
                    "Add your skills to your student profile."
                    if skill_status == "MISSING"
                    else "All required skills are present in your profile."
                    if skill_status == "MET"
                    else f"Add or develop these required skills: {', '.join(missing_skills)}."
                ),
            }
        )

    for check in checks:
        if check["status"] == "MISSING":
            missing_fields.append(check["label"])

    has_failure = any(check["status"] == "NOT_MET" for check in checks)
    has_missing = any(check["status"] == "MISSING" for check in checks)

    if has_failure:
        result_status = "INELIGIBLE"
        eligible = False
    elif has_missing:
        result_status = "INCOMPLETE_PROFILE"
        eligible = None
    else:
        result_status = "ELIGIBLE"
        eligible = True

    reasons = [check["reason"] for check in checks if check["status"] != "MET"]
    if not reasons:
        reasons = ["Your profile meets all configured eligibility criteria."]

    return {
        "status": result_status,
        "eligible": eligible,
        "checks": checks,
        "reasons": reasons,
        "missing_fields": missing_fields,
    }
