RULES = [
    {
        "id": "R01",
        "premises": {"motor_temperature": "high", "movement_status": "stalled"},
        "conclusions": {
            "finding": "Overheating motor causing stall",
            "recommendation": "Hentikan robot dan biarkan motor mendingin selama 15 menit.",
            "pause_robot": True
        },
        "reason": "Suhu motor yang tinggi dipadukan dengan status macet mengindikasikan beban berlebih pada sistem penggerak."
    },
    {
        "id": "R02",
        "premises": {"sensor_lidar": "blocked"},
        "conclusions": {
            "finding": "Lidar sensor obstruction",
            "recommendation": "Bersihkan lensa sensor Lidar dari debu atau halangan fisik.",
            "pause_robot": True
        },
        "reason": "Sensor Lidar yang terhalang membuat robot buta terhadap rintangan di depannya."
    }
]

def diagnose(facts: dict) -> dict:
    result = {
        "status": "ok", 
        "findings": [],
        "recommendations": [],
        "rule_trace": [],
        "missing_facts": []
    }
    
    known_facts = {k: v for k, v in facts.items() if v is not None}
    expected_keys = ["motor_temperature", "movement_status", "sensor_lidar"]
    
    for key in expected_keys:
        if key not in known_facts:
            result["missing_facts"].append(key)

    rules_triggered = False
    for rule in RULES:
        match = True
        for key, expected_value in rule["premises"].items():
            if known_facts.get(key) != expected_value:
                match = False
                break
        
        if match:
            rules_triggered = True
            result["findings"].append(rule["conclusions"]["finding"])
            result["recommendations"].append(rule["conclusions"]["recommendation"])
            
            # PERBAIKAN DI SINI: Menggunakan nama kunci (keys) yang disepakati persis
            result["rule_trace"].append({
                "rule_id": rule["id"],
                "premises": rule["premises"],
                "conclusions": rule["conclusions"],
                "reason": rule["reason"]
            })
            
    if not rules_triggered and result["missing_facts"]:
        result["status"] = "unknown"

    return result