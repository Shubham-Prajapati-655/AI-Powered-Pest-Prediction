def get_pest_recommendations(crop, risk_level):
    """
    Generate agronomic recommendations based on crop and predicted pest outbreak risk level.
    """
    recommendations = {
        "High": {
            "severity_badge": "🔴 HIGH RISK OUTBREAK",
            "alert_message": f"Critical pest infestation threat detected for {crop}. Immediate intervention required.",
            "cultural_control": "Ensure complete field drainage. Remove and destroy infected plant residues immediately.",
            "biological_control": "Deploy bio-pesticides (e.g., Trichogramma cards @ 5 cards/ha or Neem oil 10,000 ppm @ 3 ml/L water).",
            "chemical_control": "Spray recommended selective insecticides (e.g., Chlorantraniliprole 18.5% SC @ 0.4 ml/L) during early morning or late evening.",
            "monitoring_frequency": "Inspect crop canopy every 24 to 48 hours."
        },
        "Medium": {
            "severity_badge": "🟡 MEDIUM RISK OUTBREAK",
            "alert_message": f"Moderate pest outbreak conditions observed for {crop}. Heightened monitoring recommended.",
            "cultural_control": "Maintain balanced nitrogenous fertilizer application to prevent dense succulent growth.",
            "biological_control": "Install yellow/blue sticky traps (10-12 traps/acre) and pheromone traps for early detection.",
            "chemical_control": "Apply neem-based formulations (Neem oil 1500 ppm @ 5 ml/L water) as preventive spray.",
            "monitoring_frequency": "Inspect crop canopy twice a week."
        },
        "Low": {
            "severity_badge": "🟢 LOW RISK OUTBREAK",
            "alert_message": f"Weather conditions are currently unfavorable for severe pest outbreaks on {crop}.",
            "cultural_control": "Maintain standard farm hygiene and weed-free field borders.",
            "biological_control": "Encourage natural predators such as ladybird beetles and lacewings.",
            "chemical_control": "No chemical intervention needed at this stage.",
            "monitoring_frequency": "Standard weekly crop inspection."
        }
    }
    
    return recommendations.get(risk_level, recommendations["Medium"])

def get_crop_yield_advisory(yield_val):
    """Generate advisory based on expected crop yield per hectare."""
    if yield_val > 3500:
        return "High yield trajectory. Maintain current irrigation and nutrient schedule."
    elif yield_val > 2000:
        return "Moderate yield trajectory. Consider top-dressing nitrogen and micro-nutrients."
    else:
        return "Below-average yield expected. Evaluate soil health and pest control measures."
