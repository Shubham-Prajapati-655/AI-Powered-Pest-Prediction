"""
Step 10: Dynamic Agricultural Advisory Engine & Recommendation System.
========================================================================
Production-grade post-prediction agronomic recommendation engine.
Generates fully context-aware, farmer-friendly recommendations dynamically calibrated by:
- Target Crop & Predicted Pest Species
- Season (Summer, Monsoon, Winter, Kharif, Rabi, Zaid)
- Real-time Weather Telemetry (Temperature, Humidity, Rainfall, Wind Speed)
- Regional District & Soil Context (Soil Moisture, Soil pH, NPK levels, Organic Carbon)

CRITICAL: Operates strictly post-inference. Zero ML feature leakage.
"""
import os
import sys
import json
from typing import Dict, Any, Optional, List

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.pipeline_config import ADVISORY_KB_PATH
from utils.logger import setup_logger

logger = setup_logger("advisory_engine", "advisory.log")

_SHARED_KB: Optional[Dict[str, Any]] = None

class AdvisoryEngine:
    """Post-prediction dynamic advisory engine backed by agronomic expert knowledge."""

    def __init__(self, kb_path: str = ADVISORY_KB_PATH):
        self.kb_path = kb_path
        self._kb = self._load_knowledgebase()

    def _load_knowledgebase(self) -> Dict[str, Any]:
        """Loads recommendations JSON file if present, caching in memory."""
        global _SHARED_KB
        if _SHARED_KB is not None:
            return _SHARED_KB
        if os.path.exists(self.kb_path):
            try:
                with open(self.kb_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    logger.info(f"Advisory knowledgebase loaded with {len(data)} crop categories.")
                    _SHARED_KB = data
                    return _SHARED_KB
            except Exception as e:
                logger.error(f"Failed to load advisory JSON: {e}")
        return {}

    def get_advisory(
        self,
        crop: str,
        predicted_pest: str,
        predicted_risk: str = "Medium",
        season: Optional[str] = None,
        weather: Optional[Dict[str, Any]] = None,
        soil: Optional[Dict[str, Any]] = None,
        npk: Optional[Dict[str, float]] = None,
        district: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Retrieves tailored, dynamic agronomic recommendations strictly post-prediction.
        Context-aware inputs:
        - crop: Target Crop Name
        - predicted_pest: Rank-1 Predicted Pest
        - predicted_risk: Risk tier (High, Medium, Low - kept internally)
        - season: Current season (Summer, Monsoon, Winter, Kharif, Rabi, Zaid)
        - weather: dict with temp, humidity, rainfall, wind_speed
        - soil: dict with soil_moisture, soil_ph, organic_carbon
        - npk: dict with Nitrogen, Phosphorus, Potassium
        - district: regional district
        """
        crop_clean = str(crop or "Maize").strip()
        pest_clean = str(predicted_pest or "Stem Borer").strip()
        risk_clean = str(predicted_risk or "Medium").strip().capitalize()
        if risk_clean not in ["High", "Medium", "Low"]:
            risk_clean = "Medium"

        # Normalize weather inputs
        w = weather or {}
        temp = float(w.get("temperature", w.get("temp", 28.0)))
        humidity = float(w.get("humidity", 65.0))
        rainfall = float(w.get("rainfall_mm", w.get("rainfall", 20.0)))
        wind_speed = float(w.get("wind_speed", 10.0))

        # Normalize soil inputs
        s = soil or {}
        soil_moisture = float(s.get("soil_moisture", s.get("moisture", 50.0)))
        soil_ph = float(s.get("soil_ph", s.get("ph", 7.0)))
        org_carbon = float(s.get("organic_carbon", s.get("oc", 0.65)))

        # Normalize NPK
        npk_dict = npk or {}
        n_val = float(npk_dict.get("Nitrogen", npk_dict.get("n", 25.0)))
        p_val = float(npk_dict.get("Phosphorus", npk_dict.get("p", 18.0)))
        k_val = float(npk_dict.get("Potassium", npk_dict.get("k", 12.0)))

        # Normalize season
        season_str = str(season or "Kharif").strip()
        season_lower = season_str.lower()
        if "summer" in season_lower or "zaid" in season_lower:
            detected_season_group = "Summer"
        elif "monsoon" in season_lower or "kharif" in season_lower:
            detected_season_group = "Monsoon"
        elif "winter" in season_lower or "rabi" in season_lower:
            detected_season_group = "Winter"
        else:
            detected_season_group = "Monsoon"

        # Lookup in knowledgebase if available
        crop_kb = self._kb.get(crop_clean, {})
        pest_kb = crop_kb.get(pest_clean, {})
        kb_entry = pest_kb.get(risk_clean, pest_kb.get("Medium", {}))

        # -------------------------------------------------------------
        # DOMAIN PEST-SPECIFIC TREATMENT BASELINES
        # -------------------------------------------------------------
        pest_profiles = {
            "Fall Armyworm": {
                "treatment": "Initiate whorl-directed spray upon detecting 5% seedling or 10% vegetative leaf damage.",
                "chemical": "Chlorantraniliprole 18.5% SC or Emamectin Benzoate 5% SG directed into leaf whorls.",
                "organic": "Foliar spray of Bacillus thuringiensis (Bt) kurstaki @ 2 g/L or Beauveria bassiana @ 5 g/L.",
                "ipm": "Install pheromone traps @ 5-6 traps/acre. Practice intercropping with cowpea or desmodium to repel moths.",
                "dosage": "Chlorantraniliprole @ 0.4 ml/L (80 ml/acre) or Emamectin Benzoate @ 0.4 g/L (80 g/acre) in 200L water.",
                "phi": "14 days",
                "recovery": "Noticeable larval mortality within 24-48 hours; fresh unchewed whorl emergence within 5-7 days."
            },
            "Stem Borer": {
                "treatment": "Target young larvae before boring into central stem tissues or apply granular whorl protection.",
                "chemical": "Cartap Hydrochloride 4% G (granular) or Flubendiamide 39.35% SC (foliar spray).",
                "organic": "Release Trichogramma chilonis egg parasitoid cards @ 40,000 to 50,000 eggs/acre at 7-day intervals.",
                "ipm": "Clip seedling leaf tips before transplanting to remove egg clusters; use light traps @ 1 trap/acre.",
                "dosage": "Flubendiamide @ 0.2 ml/L (50 ml/acre) or Cartap Hydrochloride 4% G @ 8-10 kg/acre into root zone.",
                "phi": "15 days",
                "recovery": "Arrest of fresh 'dead heart' / 'white ear' development within 3-5 days; side-tillering recovery in 7-10 days."
            },
            "Pink Bollworm": {
                "treatment": "Strict monitoring of rosette flowers and green bolls with timely ovicidal or larvicidal sprays.",
                "chemical": "Profenofos 50% EC or Spinetoram 11.7% SC or Emamectin Benzoate 5% SG.",
                "organic": "Release Trichogrammatoidea bactrae @ 60,000/acre; spray Neem Seed Kernel Extract (NSKE 5%) @ 50 g/L.",
                "ipm": "Deploy Gossyplure pheromone traps @ 8-10 traps/acre. Terminate crop by mid-January to break overwintering pupae cycle.",
                "dosage": "Spinetoram @ 0.5 ml/L (100 ml/acre) or Profenofos @ 2 ml/L (400 ml/acre) in 200L water.",
                "phi": "14 days",
                "recovery": "Moth flight suppression within 3-4 days; rosette flower drop reduction within 1 week."
            },
            "Whitefly": {
                "treatment": "Target undersides of leaves early in the outbreak to prevent honeydew accumulation and leaf curl virus transmission.",
                "chemical": "Pyriproxyfen 10% EC or Diafenthiuron 50% WP or Flonicamid 50% WG.",
                "organic": "Foliar spray of cold-pressed Neem Oil 10,000 ppm @ 2 ml/L with 1 ml/L organic soap or Verticillium lecanii @ 5 g/L.",
                "ipm": "Erect bright yellow sticky traps @ 15-20 traps/acre just above crop canopy. Avoid synthetic pyrethroids which induce resurgence.",
                "dosage": "Diafenthiuron @ 1.2 g/L (250 g/acre) or Pyriproxyfen @ 1.5 ml/L (300 ml/acre) targeting lower canopy.",
                "phi": "12 days",
                "recovery": "Adult whitefly knockdown within 24 hours; reduction in nymphal colonies within 4-6 days."
            },
            "Aphid": {
                "treatment": "Control localized early colonies on tender growing shoots and flower buds before sooty mold spreads.",
                "chemical": "Thiamethoxam 25% WG or Imidacloprid 17.8% SL or Acetamiprid 20% SP.",
                "organic": "Spray 5% Neem Seed Kernel Extract (NSKE) or Fish Oil Rosin Soap (FORS) @ 25 g/L; conserve Ladybird beetles.",
                "ipm": "Install yellow sticky sheets @ 10-12 traps/acre. Conserve natural syrphid fly larvae and predatory lacewings.",
                "dosage": "Thiamethoxam 25% WG @ 0.25 g/L (50 g/acre) or Imidacloprid @ 0.3 ml/L (60 ml/acre).",
                "phi": "7-10 days",
                "recovery": "Aphid colonies dry up and drop off foliage within 36-48 hours; shoot curling ceases in 4-6 days."
            },
            "Mustard Aphid": {
                "treatment": "Scout terminal 10 cm of main inflorescence; intervene when aphid count exceeds 25-30 aphids per plant.",
                "chemical": "Dimethoate 30% EC or Oxydemeton-methyl 25% EC or Thiamethoxam 25% WG.",
                "organic": "Spray cold-pressed Neem Oil 1500 ppm @ 5 ml/L or release Chrysoperla carnea predators @ 20,000/acre.",
                "ipm": "Sow mustard early (before mid-October) to escape peak aphid flight; erect yellow water pan traps.",
                "dosage": "Dimethoate @ 1.7 ml/L (350 ml/acre) or Thiamethoxam @ 0.2 g/L (40 g/acre) in 200L water.",
                "phi": "15 days",
                "recovery": "Infestation arrested within 48 hours; flowering continues with healthy siliqua pod filling."
            },
            "Brown Planthopper": {
                "treatment": "Direct spray nozzles right at the base of rice tillers where nymphs congregate; drain excess standing water.",
                "chemical": "Trifflumezopyrim 10% SC or Pymetrozine 50% WG or Dinotefuran 20% SG.",
                "organic": "Spray Neem Oil 3000 ppm @ 3 ml/L or apply Metarhizium anisopliae bio-formulation @ 5 g/L.",
                "ipm": "Provide alleyways (30 cm gaps every 2-3 meters) for aeration and light; practice Alternate Wetting and Drying (AWD).",
                "dosage": "Trifflumezopyrim @ 0.5 ml/L (94 ml/acre) or Pymetrozine @ 0.6 g/L (120 g/acre) directed at hill base.",
                "phi": "15-21 days",
                "recovery": "Base hopper populations collapse within 24-48 hours; 'hopper burn' yellowing prevented from spreading."
            },
            "Gram Pod Borer": {
                "treatment": "Protect flowers and pod setting stages from Helicoverpa larval feeding; spray during early instar stages.",
                "chemical": "Chlorantraniliprole 18.5% SC or Emamectin Benzoate 5% SG or Indoxacarb 14.5% SC.",
                "organic": "HaNPV (Helicoverpa nuclear polyhedrosis virus) @ 250 LE/acre with 1% jaggery, or Bacillus thuringiensis (Bt) @ 2 g/L.",
                "ipm": "Plant marigold as trap crop (1 row every 10-15 rows); set up Helicoverpa pheromone traps @ 5-6/acre; install bird perches @ 20/acre.",
                "dosage": "Chlorantraniliprole @ 0.3 ml/L (60 ml/acre) or Emamectin Benzoate @ 0.4 g/L (80 g/acre).",
                "phi": "14 days",
                "recovery": "Larval cessation of feeding within 4-6 hours; zero fresh pod bores within 48 hours."
            },
            "Leaf Folder": {
                "treatment": "Spray when more than 1-2 folded leaves per hill with live caterpillars are visible across the paddy field.",
                "chemical": "Cartap Hydrochloride 50% SP or Flubendiamide 39.35% SC or Chlorantraniliprole 18.5% SC.",
                "organic": "Release Trichogramma chilonis egg cards @ 40,000/acre; spray NSKE 5% @ 50 g/L.",
                "ipm": "Pass a long bamboo pole or coir rope across paddy canopy to dislodge larvae into floodwater with predatory beetles.",
                "dosage": "Cartap Hydrochloride @ 2 g/L (400 g/acre) or Flubendiamide @ 0.2 ml/L (50 ml/acre).",
                "phi": "14 days",
                "recovery": "Larvae succumb within 48 hours; new leaves unfold without longitudinal leaf margin gluing."
            },
            "Early Shoot Borer": {
                "treatment": "Protect sugarcane young shoots within 30-100 days after planting before shoot spindle drying occurs.",
                "chemical": "Fipronil 0.3% G (soil application) or Chlorantraniliprole 18.5% SC (soil drenching along furrow).",
                "organic": "Trichogramma chilonis parasitoids @ 50,000/acre released bi-weekly; trash mulching @ 3 tons/acre.",
                "ipm": "Light earthing-up at 35-45 days after planting; trash mulching to maintain soil moisture and discourage moth oviposition.",
                "dosage": "Fipronil 0.3% G @ 10-12 kg/acre at sowing or Chlorantraniliprole 18.5% SC @ 150 ml/acre along furrow.",
                "phi": "30 days",
                "recovery": "Dead heart progression halted; compensatory tillering initiated within 10-14 days."
            },
            "Diamondback Moth": {
                "treatment": "Rotate chemical modes of action to prevent resistance; apply upon noticing small windowpane leaf punctures.",
                "chemical": "Spinosad 45% SC or Chlorantraniliprole 18.5% SC or Bacillus thuringiensis var. kurstaki.",
                "organic": "Bt kurstaki spray @ 2 g/L; release egg parasitoid Diadegma semiclausum.",
                "ipm": "Grow Indian mustard as trap crop around cole crop borders; install DBM pheromone lures @ 8-10 traps/acre.",
                "dosage": "Spinosad @ 0.3 ml/L (60 ml/acre) or Chlorantraniliprole @ 0.3 ml/L (60 ml/acre) with non-ionic surfactant.",
                "phi": "7 days",
                "recovery": "Larval paralysis within 12 hours; leaf skeletonization stops immediately."
            },
            "Armyworm": {
                "treatment": "Detect nocturnal gregarious caterpillar swarms early; apply boundary trenching and contact-stomach sprays.",
                "chemical": "Emamectin Benzoate 5% SG or Novaluron 10% EC or Chlorantraniliprole 18.5% SC.",
                "organic": "Spray Beauveria bassiana @ 5 g/L or cold-pressed Neem Oil 10,000 ppm @ 2 ml/L.",
                "ipm": "Dig boundary trenches (20 cm deep, 30 cm wide) around field edges with dusting to prevent caterpillar migration.",
                "dosage": "Emamectin Benzoate @ 0.4 g/L (80 g/acre) or Novaluron @ 1.5 ml/L (300 ml/acre).",
                "phi": "10-14 days",
                "recovery": "Active crawling caterpillars halted within 24 hours; foliage defoliation arrested."
            },
            "Cutworm": {
                "treatment": "Target nocturnal cutworms severing seedlings at ground level during night hours; apply drench around stems.",
                "chemical": "Chlorpyrifos 20% EC (collar drenching) or Chlorantraniliprole 18.5% SC.",
                "organic": "Poison baiting with rice bran (10 kg) + jaggery (1 kg) + Chlorpyrifos (100 ml) or Bt granules scattered around hills.",
                "ipm": "Flood fields prior to planting to expose subterranean larvae to birds; handpick larvae under clods in early morning.",
                "dosage": "Chlorpyrifos @ 3 ml/L water drenched around base of seedling stems in late evening.",
                "phi": "21 days",
                "recovery": "Seedling snipping stops within 24-36 hours; gap-filling or compensatory branching proceeds."
            },
            "Pyrilla": {
                "treatment": "Manage leafhopper colonies on sugarcane foliage; conserve Epiricania melanoleuca parasitoid cocoons.",
                "chemical": "Malathion 50% EC or Dimethoate 30% EC foliar spray.",
                "organic": "Conserve or redistribute Epiricania melanoleuca cocoons @ 400-500 cocoons/acre.",
                "ipm": "Strip dry lower cane leaves where nymphs cluster; avoid waterlogged saline conditions.",
                "dosage": "Malathion 50% EC @ 2 ml/L (400 ml/acre) or Dimethoate 30% EC @ 1.5 ml/L (300 ml/acre).",
                "phi": "14 days",
                "recovery": "Hopper jumping activity drops drastically within 48 hours; honeydew deposit stops."
            },
            "Spodoptera": {
                "treatment": "Treat young gregarious caterpillar clusters on foliage before they scatter into individual solitary chewers.",
                "chemical": "Emamectin Benzoate 5% SG or Spinetoram 11.7% SC or Novaluron 10% EC.",
                "organic": "SlNPV (Spodoptera litura nuclear polyhedrosis virus) @ 250 LE/acre or Bt kurstaki @ 2 g/L.",
                "ipm": "Install Spodolure pheromone traps @ 6-8 traps/acre; handpick skeletonized leaves containing young larval clusters.",
                "dosage": "Emamectin Benzoate @ 0.4 g/L (80 g/acre) or Spinetoram @ 0.5 ml/L (100 ml/acre).",
                "phi": "14 days",
                "recovery": "Feeding ceases in 2-4 hours; complete drop of dead caterpillars from plant in 48 hours."
            },
            "Leaf Miner": {
                "treatment": "Intervene when serpentine silvery mines appear on more than 10-15% of green leaves.",
                "chemical": "Abamectin 1.9% EC or Cartap Hydrochloride 50% SP or Chlorantraniliprole 18.5% SC.",
                "organic": "Spray cold-pressed Neem Oil 1500 ppm @ 5 ml/L; conserve Diglyphus isaea parasitoid wasps.",
                "ipm": "Remove and bury heavily mined basal leaves; erect yellow sticky traps to capture adult flies.",
                "dosage": "Abamectin @ 0.5 ml/L (100 ml/acre) or Cartap Hydrochloride @ 1.5 g/L (300 g/acre).",
                "phi": "7-10 days",
                "recovery": "Mining activity arrested; newly emerging foliage remains completely clear and unblemished."
            },
            "Shoot Fly": {
                "treatment": "Target seedling stage (within 4 weeks of emergence); apply systemic seed treatment or granule placement.",
                "chemical": "Thiamethoxam 30% FS (seed treatment) or Chlorantraniliprole 18.5% SC foliar drench.",
                "organic": "Neem cake soil amendment @ 100 kg/acre at sowing; spray NSKE 5% @ 50 g/L at 7 & 14 days after emergence.",
                "ipm": "Sow crop immediately with onset of monsoon to escape fly emergence; increase seed rate by 10% for thinning.",
                "dosage": "Thiamethoxam 30% FS seed coating @ 10 ml/kg seed or spray Chlorantraniliprole @ 0.3 ml/L at 7 days.",
                "phi": "21 days",
                "recovery": "Shoot dieback ceases; healthy auxiliary tillers take over within 7-12 days."
            },
            "Termite": {
                "treatment": "Treat soil zone around plant roots or incorporate termiticide during field preparation.",
                "chemical": "Chlorpyrifos 20% EC or Fipronil 0.3% G applied to soil with irrigation water.",
                "organic": "Drench soil with Metarhizium anisopliae bio-formulation @ 10 g/L or incorporate neem cake @ 150 kg/acre.",
                "ipm": "Destroy termite mounds near field borders; avoid using un-decomposed farmyard manure which attracts worker termites.",
                "dosage": "Chlorpyrifos 20% EC @ 3-4 ml/L applied with irrigation stream or Fipronil 0.3% G @ 10 kg/acre.",
                "phi": "30 days",
                "recovery": "Subterranean root girdling halts immediately; wilting stops and standing crop recovers vigor."
            },
            "Pod Borer": {
                "treatment": "Scout flower racemes and green pods; spray at 50% flowering and early pod stage.",
                "chemical": "Chlorantraniliprole 18.5% SC or Flubendiamide 39.35% SC or Emamectin Benzoate 5% SG.",
                "organic": "Spray HaNPV @ 250 LE/acre + 1% jaggery, or Bacillus thuringiensis (Bt) @ 2 g/L.",
                "ipm": "Erect bird perches @ 20/acre to encourage insectivorous birds; shake plants over cloth to collect caterpillars.",
                "dosage": "Chlorantraniliprole @ 0.3 ml/L (60 ml/acre) or Flubendiamide @ 0.2 ml/L (40 ml/acre).",
                "phi": "14 days",
                "recovery": "Flower drop stops; pods fill cleanly without boreholes."
            },
            "Pod Fly": {
                "treatment": "Target adult flies during pod maturation; systemic penetration is essential as maggots feed inside pods.",
                "chemical": "Monocrotophos 36% SL or Dimethoate 30% EC or Spinosad 45% SC.",
                "organic": "Neem Seed Kernel Extract (NSKE 5%) sprayed at pod initiation and 10 days later.",
                "ipm": "Harvest crop promptly once pods mature; plow field deeply in summer to expose puparia to birds.",
                "dosage": "Dimethoate 30% EC @ 1.7 ml/L (350 ml/acre) or Spinosad @ 0.3 ml/L (60 ml/acre).",
                "phi": "15 days",
                "recovery": "Adult fly oviposition prevented; seed grain development proceeds undamaged."
            }
        }

        # Fallback profile for general pests
        base_p = pest_profiles.get(pest_clean, {
            "treatment": f"Conduct thorough field scouting and apply targeted IPM protocol against {pest_clean}.",
            "chemical": kb_entry.get("pesticide", "Chlorantraniliprole 18.5% SC or Emamectin Benzoate 5% SG"),
            "organic": kb_entry.get("organic_control", "Neem Seed Kernel Extract (NSKE 5%) @ 50 g/L or cold-pressed Neem Oil @ 5 ml/L"),
            "ipm": "Deploy sticky or pheromone traps @ 10-12/acre; conserve beneficial natural predators like ladybird beetles.",
            "dosage": kb_entry.get("dosage", "0.3 ml/L water foliar spray (60-80 ml/acre in 200L water)"),
            "phi": "14 days",
            "recovery": f"Reduction in active {pest_clean} feeding within 36-48 hours; complete plant recovery in 7-10 days."
        })

        # -------------------------------------------------------------
        # STEP 7: DYNAMIC SEASONAL CALIBRATION
        # -------------------------------------------------------------
        season_advisories = {
            "Summer": {
                "spray_timing": "Early Morning (6:00 AM - 8:30 AM) or Late Evening (5:30 PM - 7:00 PM). Strictly avoid midday spraying (11 AM - 3 PM) to prevent rapid chemical evaporation and leaf scorch.",
                "irrigation": "Apply light, frequent evening irrigations. Ensure field does not enter drought stress which multiplies sap-sucking pest damage.",
                "fertilizer_mod": "Strictly withhold excess Urea during dry heat; supplement with 1% Potassium Nitrate (KNO3) foliar spray to maintain leaf turgor and cellular cuticle thickness.",
                "precaution": "Do not spray Emulsifiable Concentrate (EC) formulations under scorching sunshine (>34°C). Always add 1 ml/L non-ionic wetting agent.",
                "action_prefix": "Under hot, dry summer conditions, pests multiply rapidly while crops face heat stress."
            },
            "Monsoon": {
                "spray_timing": "Target clear sunny weather breaks. Ensure at least 2 to 3 rain-free hours after application so spray does not wash off.",
                "irrigation": "Check field drainage channels immediately. Prevent water stagnation which promotes root rot and fungal secondary infections.",
                "fertilizer_mod": "Apply Nitrogen only in split doses; never broadcast urea right before rain. Supplement with Potash @ 25 kg/ha to prevent plant lodging.",
                "precaution": "MUST mix an organosilicone rain-fast sticker/adjuvant (1 ml/L) with all foliar sprays. Postpone spray if continuous downpour is imminent.",
                "action_prefix": "Humid monsoon weather accelerates both pest hatching and foliar fungal complications."
            },
            "Winter": {
                "spray_timing": "Mid-Morning (10:00 AM - 1:00 PM) strictly AFTER morning dew has fully evaporated from crop leaves.",
                "irrigation": "Provide moderate interval irrigation during morning hours. Avoid soaking foliage late in the day to minimize overnight chilling.",
                "fertilizer_mod": "Apply Sulfur 80% WDG @ 10 kg/acre alongside balanced NPK to provide thermal root protection and enhance natural glucosinolate plant defense.",
                "precaution": "Never spray on dew-covered foliage as moisture causes heavy chemical run-off into the soil without touching the pest.",
                "action_prefix": "Cool winter temperatures slow insect metabolism; morning dew requires adjusted spray timing."
            }
        }
        season_ctx = season_advisories.get(detected_season_group, season_advisories["Monsoon"])

        # -------------------------------------------------------------
        # STEP 6: DYNAMIC WEATHER & MICROCLIMATE SENSITIVITY
        # -------------------------------------------------------------
        weather_modifiers = []
        if temp > 33.0:
            weather_modifiers.append(f"High thermal stress ({temp:.1f}°C) detected: Spray only during twilight hours with abundant water volume (200-250 L/acre) to prevent phytotoxicity.")
        elif temp < 18.0:
            weather_modifiers.append(f"Cool ambient regime ({temp:.1f}°C): Slower insect metabolism; allow 48-72 hours for systemic insecticides to exhibit full knockdown.")

        if humidity > 78.0:
            weather_modifiers.append(f"High atmospheric humidity ({humidity:.1f}% RH): Excellent conditions for beneficial bio-pesticides (Beauveria/Metarhizium); however, monitor for secondary fungal mold.")
        elif humidity < 40.0:
            weather_modifiers.append(f"Dry atmospheric conditions ({humidity:.1f}% RH): Favors rapid mite and sucking pest flare-up; prioritize systemic treatments with adequate coverage.")

        if rainfall > 25.0:
            weather_modifiers.append(f"Recent rainfall ({rainfall:.1f} mm): Clear furrows immediately. Postpone foliar spraying until foliage has fully dried.")

        if wind_speed > 13.0:
            weather_modifiers.append(f"Elevated wind velocity ({wind_speed:.1f} km/h): High spray drift risk! Lower spray boom height, use flood-jet nozzles, or delay until wind drops below 10 km/h.")

        # -------------------------------------------------------------
        # SOIL & NPK DYNAMIC CUSTOMIZATION
        # -------------------------------------------------------------
        soil_fert_notes = []
        # Crop baseline fertilizer
        crop_base_fert = {
            "Rice": "Apply balanced NPK 28-28 @ 50 kg/ha in splits. Apply MOP (Potassium) @ 20 kg/ha to strengthen stalk resistance against borers and planthoppers.",
            "Cotton": "Apply 17-17-17 @ 60 kg/ha with micronutrient spray (Zinc + Boron). Spray 1% Potassium Nitrate foliar during boll development.",
            "Wheat": "Apply 28-28 @ 40 kg/ha before crown root initiation irrigation; apply Potassium Sulfate @ 15 kg/ha.",
            "Sugarcane": "Apply Potash @ 30 kg/ha along with earthing up. Apply 17-17-17 @ 100 kg/ha in two split furrow doses.",
            "Soybean": "Foliar spray of 0.5% soluble Boron + 1% Potash. Soybean fixes atmospheric nitrogen; avoid top-dressing urea.",
            "Maize": "Apply Potash @ 25 kg/ha to reinforce stalk strength against armyworm/borers. Apply 20-20-0 @ 50 kg/ha.",
            "Gram": "Apply DAP @ 35 kg/ha with sulfur @ 15 kg/ha. Avoid excess nitrogen which delays flowering.",
            "Mustard": "Apply Sulfur 80% WDG @ 10 kg/acre to boost glucosinolate plant defense against mustard aphids. Apply 20-20 @ 45 kg/ha.",
            "Groundnut": "Apply Gypsum @ 200 kg/ha at pegging stage to harden subterranean pods against soil pests.",
            "Tur (Arhar)": "Spray 1% Potassium Chloride to decrease flower drop under pest stress. Apply DAP @ 40 kg/ha."
        }
        soil_fert_notes.append(crop_base_fert.get(crop_clean, "Apply balanced NPK according to regional soil health card recommendations."))

        if n_val > 28.0:
            soil_fert_notes.append(f"⚠️ High Soil Nitrogen ({n_val:.1f} kg/ha): Excess succulent growth attracts intense {pest_clean} feeding. Strictly suspend top-dressing Urea.")
        elif n_val < 15.0:
            soil_fert_notes.append(f"Low Soil Nitrogen ({n_val:.1f} kg/ha): Supplement with a light split dose of nitrogen once pest pressure subsides to aid vegetative recovery.")

        if k_val < 13.0:
            soil_fert_notes.append(f"Low Soil Potassium ({k_val:.1f} kg/ha): Plants have weakened cell walls. Apply MOP @ 20 kg/acre or 1% Potash foliar spray to reinforce natural plant cuticle defense against {pest_clean}.")

        if p_val < 14.0:
            soil_fert_notes.append(f"Deficient Soil Phosphorus ({p_val:.1f} kg/ha): Supplement with DAP/SSP to accelerate root regeneration.")

        if soil_moisture < 35.0:
            soil_fert_notes.append(f"Low Soil Moisture ({soil_moisture:.1f}%): Irrigate 12-24 hours prior to chemical application to avoid leaf scorch on wilted crop.")
        elif soil_moisture > 65.0:
            soil_fert_notes.append(f"High Soil Moisture ({soil_moisture:.1f}%): Improve field drainage to reduce root hypoxia.")

        if soil_ph < 6.2:
            soil_fert_notes.append(f"Acidic Soil (pH {soil_ph:.1f}): Apply agricultural lime during inter-cultivation to correct nutrient lockup.")
        elif soil_ph > 7.8:
            soil_fert_notes.append(f"Alkaline Soil (pH {soil_ph:.1f}): Apply chelated Zinc and micronutrient foliar spray to boost plant vigor.")

        if org_carbon < 0.50:
            soil_fert_notes.append(f"Low Soil Organic Carbon ({org_carbon:.2f}%): Incorporate well-decomposed FYM or vermicompost @ 2-3 tons/acre after harvest to foster beneficial soil microbiology.")

        # -------------------------------------------------------------
        # STEP 8: SYNTHESIZE COMPLETE FARMER-FRIENDLY ADVISORY
        # -------------------------------------------------------------
        final_treatment = f"{season_ctx['action_prefix']} {base_p['treatment']}"
        final_chemical = base_p["chemical"]
        final_organic = base_p["organic"]
        final_ipm = base_p["ipm"]
        final_dosage = base_p["dosage"]
        
        # Spray Timing with weather adjustments
        spray_timing_parts = [season_ctx["spray_timing"]]
        if weather_modifiers:
            spray_timing_parts.extend(weather_modifiers)
        final_spray_timing = " ".join(spray_timing_parts)

        # Fertilizer
        final_fertilizer = " ".join(soil_fert_notes)

        # Prevention practices
        preventive_measures = [
            f"Field Sanitation: Remove and destroy alternate weed hosts along bunds and borders that shelter {pest_clean}.",
            f"Drainage & Water Management: {season_ctx['irrigation']}",
            f"Monitoring & Traps: {base_p['ipm']}",
            f"Crop Rotation: After harvesting {crop_clean}, avoid immediately replanting susceptible host varieties."
        ]

        # Field monitoring tips
        field_monitoring_tips = [
            f"Examine 20 random plants selected across a 'W' pattern walking through the field twice every week.",
            f"Carefully inspect the undersides of leaves, tender shoots, and whorls for early {pest_clean} eggs and nymphs.",
            f"Check pheromone and yellow sticky traps every 3 days; clean or replace sticky liners once covered with dust or insects.",
            f"Initiate control measures promptly when 5-10% of scouted plants exhibit active feeding symptoms."
        ]

        # Safety precautions
        safety_precautions = [
            "Wear full protective clothing: rubber gloves, face mask, eye goggles, and boots during spray preparation and spraying.",
            "Spray strictly in the direction of the wind; never spray against the wind to prevent chemical inhalation or dermal exposure.",
            "Avoid spraying during peak honeybee foraging hours (10:00 AM - 3:00 PM) to protect beneficial pollinators.",
            "Keep domestic cattle, goats, and children away from the treated field for at least 24 hours.",
            "Safely puncture and deeply bury empty pesticide containers away from drinking water wells and streams."
        ]

        harvest_interval = base_p.get("phi", "14 days")
        expected_recovery = base_p.get("recovery", "Arrest of pest damage within 48 hours; active crop recovery within 7-10 days.")

        return {
            # Core Metadata
            "crop": crop_clean,
            "predicted_pest": pest_clean,
            "predicted_risk": risk_clean,
            "season": season_str,
            "detected_season_group": detected_season_group,

            # Step 8 All 12 Required Fields
            "recommended_treatment": final_treatment,
            "chemical_control": final_chemical,
            "organic_control": final_organic,
            "ipm": final_ipm,
            "dosage": final_dosage,
            "spray_timing": final_spray_timing,
            "recommended_fertilizer": final_fertilizer,
            "preventive_measures": preventive_measures,
            "field_monitoring_tips": field_monitoring_tips,
            "safety_precautions": safety_precautions,
            "harvest_interval": harvest_interval,
            "expected_recovery": expected_recovery,

            # Backward compatibility fields for existing tests and callers
            "recommended_pesticide": final_chemical,
            "pesticide": final_chemical,
            "safety_notes": " ".join(safety_precautions[:2]),
            "prevention": preventive_measures,
            "Recommended_Pesticide": final_chemical,
            "Organic_Control": final_organic,
            "Chemical_Control": final_chemical,
            "Recommended_Fertilizer": final_fertilizer,
            "Safety_Notes": " ".join(safety_precautions[:2]),
            "Preventive_Measures": preventive_measures
        }

if __name__ == "__main__":
    engine = AdvisoryEngine()
    print("Testing Fall Armyworm in Maize (Summer):")
    adv_summer = engine.get_advisory("Maize", "Fall Armyworm", "High", season="Summer", weather={"temperature": 36.0, "humidity": 45.0, "wind_speed": 8.0})
    print(json.dumps(adv_summer, indent=2))
