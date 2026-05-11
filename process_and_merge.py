import pandas as pd
import numpy as np
import re
import json
import hashlib
import logging
from datetime import datetime
from difflib import SequenceMatcher

logger = logging.getLogger("processor")


# ═══════════════════════════════════════════════════
# COMPREHENSIVE BRAND/MODEL DATABASE
# ═══════════════════════════════════════════════════

BRAND_MODEL_DB = {
    "Toyota": {
        "models": ["Camry", "Corolla", "Land Cruiser", "Prado", "RAV4", "Yaris",
                    "Fortuner", "Hilux", "Avalon", "Supra", "86", "C-HR",
                    "Highlander", "Rush", "Innova", "Sequoia", "Tundra", "4Runner",
                    "Crown", "GR86", "bZ4X", "Veloz"],
        "tier_default": "mainstream",
        "origin": "Japanese",
    },
    "Nissan": {
        "models": ["Patrol", "Altima", "Maxima", "X-Trail", "Pathfinder", "Kicks",
                    "Sentra", "Sunny", "Juke", "Navara", "Tiida", "370Z", "GT-R",
                    "Murano", "Rogue", "Armada", "Titan", "Leaf", "Ariya", "Z"],
        "tier_default": "mainstream",
        "origin": "Japanese",
    },
    "Honda": {
        "models": ["Civic", "Accord", "CR-V", "HR-V", "Pilot", "City", "Jazz",
                    "Odyssey", "Ridgeline", "Passport", "Fit", "e:NY1", "ZR-V"],
        "tier_default": "mainstream",
        "origin": "Japanese",
    },
    "Hyundai": {
        "models": ["Tucson", "Elantra", "Sonata", "Santa Fe", "Accent", "Creta",
                    "Kona", "Palisade", "Venue", "Ioniq", "Ioniq 5", "Ioniq 6",
                    "i10", "i20", "i30", "Staria", "Genesis"],  # Note: Genesis is separate brand
        "tier_default": "mainstream",
        "origin": "Korean",
    },
    "Kia": {
        "models": ["Sportage", "Sorento", "Forte", "Optima", "K5", "Seltos",
                    "Telluride", "Carnival", "Soul", "Stinger", "EV6", "EV9",
                    "Picanto", "Rio", "Cerato", "Niro"],
        "tier_default": "mainstream",
        "origin": "Korean",
    },
    "Mercedes-Benz": {
        "models": ["A-Class", "C-Class", "E-Class", "S-Class", "GLA", "GLB",
                    "GLC", "GLE", "GLS", "G-Class", "CLA", "CLS", "AMG GT",
                    "EQA", "EQB", "EQC", "EQE", "EQS", "Maybach", "SL", "SLC",
                    "V-Class", "Sprinter"],
        "aliases": ["Mercedes", "Benz", "MB"],
        "tier_default": "luxury",
        "origin": "German",
    },
    "BMW": {
        "models": ["1 Series", "2 Series", "3 Series", "4 Series", "5 Series",
                    "6 Series", "7 Series", "8 Series", "X1", "X2", "X3", "X4",
                    "X5", "X6", "X7", "Z4", "iX", "iX3", "i3", "i4", "i5", "i7",
                    "XM", "M2", "M3", "M4", "M5", "M8"],
        "tier_default": "luxury",
        "origin": "German",
    },
    "Audi": {
        "models": ["A3", "A4", "A5", "A6", "A7", "A8", "Q2", "Q3", "Q5", "Q7",
                    "Q8", "e-tron", "e-tron GT", "RS3", "RS5", "RS6", "RS7",
                    "S3", "S4", "S5", "TT", "R8"],
        "tier_default": "luxury",
        "origin": "German",
    },
    "Porsche": {
        "models": ["911", "Cayenne", "Macan", "Panamera", "Taycan", "718",
                    "Cayman", "Boxster"],
        "tier_default": "ultra_luxury",
        "origin": "German",
    },
    "Lamborghini": {
        "models": ["Urus", "Huracan", "Aventador", "Revuelto", "Gallardo"],
        "tier_default": "exotic",
        "origin": "Italian",
    },
    "Ferrari": {
        "models": ["F8", "Roma", "SF90", "296", "812", "Purosangue", "488",
                    "Portofino", "California"],
        "tier_default": "exotic",
        "origin": "Italian",
    },
    "Rolls-Royce": {
        "models": ["Phantom", "Ghost", "Wraith", "Dawn", "Cullinan", "Spectre"],
        "aliases": ["Rolls Royce", "RollsRoyce"],
        "tier_default": "exotic",
        "origin": "British",
    },
    "Bentley": {
        "models": ["Continental", "Flying Spur", "Bentayga"],
        "tier_default": "exotic",
        "origin": "British",
    },
    "Land Rover": {
        "models": ["Range Rover", "Range Rover Sport", "Defender", "Discovery",
                    "Evoque", "Velar", "Discovery Sport", "Freelander"],
        "aliases": ["Range Rover", "LandRover"],
        "tier_default": "luxury",
        "origin": "British",
    },
    "Lexus": {
        "models": ["ES", "IS", "LS", "GS", "NX", "RX", "GX", "LX", "UX",
                    "LC", "RC", "RZ"],
        "tier_default": "premium",
        "origin": "Japanese",
    },
    "Chevrolet": {
        "models": ["Tahoe", "Suburban", "Silverado", "Camaro", "Corvette",
                    "Malibu", "Equinox", "Blazer", "Traverse", "Trax",
                    "Colorado", "Captiva", "Spark", "Cruze", "Impala"],
        "tier_default": "mainstream",
        "origin": "American",
    },
    "Ford": {
        "models": ["Mustang", "Explorer", "Expedition", "F-150", "Ranger",
                    "Edge", "Escape", "Bronco", "EcoSport", "Territory",
                    "Taurus", "Fusion", "Focus", "Mach-E"],
        "tier_default": "mainstream",
        "origin": "American",
    },
    "Dodge": {
        "models": ["Charger", "Challenger", "Durango", "Hornet", "Ram"],
        "tier_default": "mainstream",
        "origin": "American",
    },
    "Jeep": {
        "models": ["Wrangler", "Grand Cherokee", "Cherokee", "Compass",
                    "Renegade", "Gladiator"],
        "tier_default": "mainstream",
        "origin": "American",
    },
    "GMC": {
        "models": ["Sierra", "Yukon", "Terrain", "Acadia", "Canyon", "Hummer EV"],
        "tier_default": "mainstream",
        "origin": "American",
    },
    "Cadillac": {
        "models": ["Escalade", "CT4", "CT5", "XT4", "XT5", "XT6", "Lyriq"],
        "tier_default": "luxury",
        "origin": "American",
    },
    "Lincoln": {
        "models": ["Navigator", "Aviator", "Corsair", "Nautilus"],
        "tier_default": "luxury",
        "origin": "American",
    },
    "Mitsubishi": {
        "models": ["Pajero", "Outlander", "Eclipse Cross", "ASX", "L200",
                    "Lancer", "Montero"],
        "tier_default": "mainstream",
        "origin": "Japanese",
    },
    "Mazda": {
        "models": ["3", "6", "CX-3", "CX-5", "CX-9", "CX-30", "CX-50",
                    "CX-60", "CX-90", "MX-5", "MX-30"],
        "tier_default": "mainstream",
        "origin": "Japanese",
    },
    "Suzuki": {
        "models": ["Jimny", "Swift", "Vitara", "Baleno", "Ertiga", "Grand Vitara",
                    "S-Cross", "Dzire", "Celerio", "Alto"],
        "tier_default": "budget",
        "origin": "Japanese",
    },
    "Volkswagen": {
        "models": ["Golf", "Tiguan", "Touareg", "Passat", "Polo", "Jetta",
                    "Atlas", "Teramont", "T-Roc", "T-Cross", "ID.4", "ID.6",
                    "Arteon", "Taos"],
        "aliases": ["VW"],
        "tier_default": "mainstream",
        "origin": "German",
    },
    "Tesla": {
        "models": ["Model 3", "Model Y", "Model S", "Model X", "Cybertruck"],
        "tier_default": "premium",
        "origin": "American",
        "all_electric": True,
    },
    "Volvo": {
        "models": ["XC40", "XC60", "XC90", "S60", "S90", "V60", "V90",
                    "C40", "EX30", "EX90"],
        "tier_default": "premium",
        "origin": "Swedish",
    },
    "Peugeot": {
        "models": ["208", "308", "408", "508", "2008", "3008", "5008"],
        "tier_default": "mainstream",
        "origin": "French",
    },
    "Renault": {
        "models": ["Duster", "Koleos", "Captur", "Megane", "Talisman",
                    "Symbol", "Logan"],
        "tier_default": "budget",
        "origin": "French",
    },
    "Genesis": {
        "models": ["G70", "G80", "G90", "GV60", "GV70", "GV80", "Electrified G80"],
        "tier_default": "luxury",
        "origin": "Korean",
    },
    "Maserati": {
        "models": ["Ghibli", "Levante", "Quattroporte", "MC20", "Grecale", "GranTurismo"],
        "tier_default": "ultra_luxury",
        "origin": "Italian",
    },
    "Jaguar": {
        "models": ["F-Pace", "E-Pace", "F-Type", "XE", "XF", "XJ", "I-Pace"],
        "tier_default": "luxury",
        "origin": "British",
    },
    "Infiniti": {
        "models": ["Q50", "Q60", "QX50", "QX55", "QX60", "QX80"],
        "tier_default": "premium",
        "origin": "Japanese",
    },
    "Acura": {
        "models": ["MDX", "RDX", "TLX", "Integra", "ZDX"],
        "tier_default": "premium",
        "origin": "Japanese",
    },
    "Changan": {
        "models": ["CS35", "CS55", "CS75", "CS85", "CS95", "Alsvin", "Eado",
                    "UNI-T", "UNI-K", "UNI-V"],
        "tier_default": "budget",
        "origin": "Chinese",
    },
    "Chery": {
        "models": ["Tiggo 4", "Tiggo 7", "Tiggo 8", "Arrizo 6"],
        "tier_default": "budget",
        "origin": "Chinese",
    },
    "Haval": {
        "models": ["H6", "H9", "Jolion", "Dargo"],
        "tier_default": "budget",
        "origin": "Chinese",
    },
    "MG": {
        "models": ["ZS", "HS", "RX5", "5", "GT", "MG4", "MG7", "Whale"],
        "tier_default": "budget",
        "origin": "Chinese",
    },
    "BYD": {
        "models": ["Atto 3", "Han", "Tang", "Seal", "Dolphin", "Song Plus"],
        "tier_default": "mainstream",
        "origin": "Chinese",
        "all_electric": True,
    },
    "Jetour": {
        "models": ["X70", "X90", "Dashing", "T2"],
        "tier_default": "budget",
        "origin": "Chinese",
    },
    "GAC": {
        "models": ["GS3", "GS4", "GS5", "GS8", "Emkoo", "Emzoom"],
        "tier_default": "budget",
        "origin": "Chinese",
    },
    "Geely": {
        "models": ["Coolray", "Azkarra", "Emgrand", "Monjaro", "Starray"],
        "tier_default": "budget",
        "origin": "Chinese",
    },
}


# ═══════════════════════════════════════════════════
# BODY TYPE DETECTION RULES
# ═══════════════════════════════════════════════════

BODY_TYPE_RULES = {
    "SUV": {
        "keywords": ["suv", "crossover"],
        "models": ["Land Cruiser", "Prado", "Patrol", "X-Trail", "CR-V", "RAV4",
                    "Tucson", "Santa Fe", "Sportage", "Tahoe", "Suburban", "Yukon",
                    "Escalade", "Navigator", "Explorer", "Expedition", "Wrangler",
                    "Grand Cherokee", "Defender", "Range Rover", "Cayenne", "Macan",
                    "Urus", "GLS", "GLE", "GLC", "GLA", "X1", "X3", "X5", "X7",
                    "Q3", "Q5", "Q7", "Q8", "Fortuner", "Highlander", "Palisade",
                    "Telluride", "Sorento", "Durango", "4Runner", "Sequoia",
                    "Bronco", "Levante", "Purosangue", "Cullinan", "Bentayga",
                    "F-Pace", "E-Pace", "Tiguan", "Touareg", "XC40", "XC60", "XC90",
                    "Jolion", "Dargo", "H6", "H9"],
    },
    "Sedan": {
        "keywords": ["sedan", "saloon"],
        "models": ["Camry", "Corolla", "Altima", "Maxima", "Civic", "Accord",
                    "Elantra", "Sonata", "K5", "Optima", "Malibu", "Impala",
                    "Charger", "Taurus", "Fusion", "A-Class", "C-Class", "E-Class",
                    "S-Class", "3 Series", "5 Series", "7 Series", "A3", "A4", "A6",
                    "A8", "Panamera", "Phantom", "Ghost", "Flying Spur",
                    "ES", "IS", "LS", "GS", "Ghibli", "Quattroporte",
                    "Model 3", "Model S", "S60", "S90"],
    },
    "Coupe": {
        "keywords": ["coupe", "coupé"],
        "models": ["Mustang", "Camaro", "Challenger", "911", "718", "Cayman",
                    "Supra", "86", "GR86", "370Z", "Z", "M2", "M4", "RC",
                    "AMG GT", "F-Type", "R8", "Huracan", "Aventador", "Corvette",
                    "LC", "8 Series", "CLA", "GT-R", "MC20"],
    },
    "Convertible": {
        "keywords": ["convertible", "cabriolet", "roadster", "spider", "spyder"],
        "models": ["Boxster", "MX-5", "SL", "Z4", "Dawn", "California"],
    },
    "Pickup": {
        "keywords": ["pickup", "truck", "pick-up"],
        "models": ["Hilux", "Ranger", "Navara", "F-150", "Silverado",
                    "Sierra", "Colorado", "Canyon", "Tundra", "Ram",
                    "Gladiator", "Ridgeline", "L200", "Cybertruck"],
    },
    "Hatchback": {
        "keywords": ["hatchback", "hatch"],
        "models": ["Golf", "Polo", "Yaris", "Jazz", "Fit", "Swift", "i10",
                    "i20", "i30", "Picanto", "Rio", "208", "308", "Baleno",
                    "Celerio", "Alto", "Kicks", "MG4"],
    },
    "Van/MPV": {
        "keywords": ["van", "mpv", "minivan"],
        "models": ["Carnival", "Odyssey", "Staria", "V-Class", "Innova", "Ertiga"],
    },
    "Wagon": {
        "keywords": ["wagon", "estate", "touring", "avant"],
        "models": ["V60", "V90"],
    },
}


# ═══════════════════════════════════════════════════
# MARKET TIER CONFIGURATION
# ═══════════════════════════════════════════════════

PRICE_TIERS = {
    "Budget":       {"min": 0,         "max": 30_000},
    "Economy":      {"min": 30_001,    "max": 60_000},
    "Mid-Range":    {"min": 60_001,    "max": 120_000},
    "Premium":      {"min": 120_001,   "max": 250_000},
    "Luxury":       {"min": 250_001,   "max": 500_000},
    "Ultra-Luxury": {"min": 500_001,   "max": 1_500_000},
    "Exotic":       {"min": 1_500_001, "max": 50_000_000},
}


# ═══════════════════════════════════════════════════
# ENHANCED PROCESSOR CLASS
# ═══════════════════════════════════════════════════

class EnhancedProcessor:
    """
    Advanced data processor with:
    - Fuzzy brand/model matching
    - Statistical outlier detection
    - Smart deduplication using content hashing
    - Cross-source validation
    - Missing value imputation
    """

    def __init__(self, dubizzle_data=None, dubicars_data=None):
        self.dubizzle_raw = dubizzle_data or []
        self.dubicars_raw = dubicars_data or []
        self.df = None
        self.quality_report = {}

    def run_pipeline(self):
        """Execute the full processing pipeline."""
        logger.info("Starting enhanced processing pipeline...")

        # Step 1: Create DataFrame
        self.df = pd.DataFrame(self.dubizzle_raw + self.dubicars_raw)
        logger.info(f"Raw records: {len(self.df)}")

        # Step 2: Basic cleaning
        self._clean_basic_fields()

        # Step 3: Brand/Model extraction
        self._extract_brand_model()

        # Step 4: Enrich with heuristics
        self._detect_body_type()
        self._detect_fuel_type()
        self._detect_transmission()
        self._detect_specs_origin()
        self._detect_seller_type()

        # Step 5: Market classification
        self._classify_price_tier()
        self._calculate_age_and_depreciation()

        # Step 6: Statistical cleaning
        self._remove_price_outliers()

        # Step 7: Smart deduplication
        self._smart_deduplicate()

        # Step 8: Data quality scoring
        self._score_data_quality()

        # Step 9: Cross-source price validation
        self._cross_source_validation()

        logger.info(f"Final clean records: {len(self.df)}")
        self._generate_quality_report()

        return self.df

    # ─── STEP 2: Basic Cleaning ───

    def _clean_basic_fields(self):
        """Clean and normalize basic fields."""
        # Price cleaning
        self.df["price"] = pd.to_numeric(self.df["price"], errors="coerce")
        self.df = self.df[self.df["price"].notna()].copy()
        self.df = self.df[(self.df["price"] >= 3000) & (self.df["price"] <= 50_000_000)].copy()

        # Year cleaning
        current_year = datetime.now().year
        self.df["year"] = pd.to_numeric(self.df["year"], errors="coerce")
        self.df.loc[
            (self.df["year"] < 1990) | (self.df["year"] > current_year + 1), "year"
        ] = np.nan

        # Mileage cleaning
        self.df["mileage"] = pd.to_numeric(self.df["mileage"], errors="coerce")
        self.df.loc[self.df["mileage"] > 500_000, "mileage"] = np.nan
        self.df.loc[self.df["mileage"] < 0, "mileage"] = np.nan

        # Title cleaning
        self.df["title"] = self.df["title"].astype(str).str.strip()

        # Normalize strings
        for col in ["location", "color", "fuel_type", "transmission", "body_type"]:
            if col in self.df.columns:
                self.df[col] = self.df[col].astype(str).str.strip().str.title()
                self.df[col] = self.df[col].replace({"Nan": np.nan, "None": np.nan, "": np.nan})

        logger.info(f"After basic cleaning: {len(self.df)} records")

    # ─── STEP 3: Brand/Model Extraction ───

    def _extract_brand_model(self):
        """Intelligent brand and model extraction with fuzzy matching."""
        brands = []
        models = []

        # Build a reverse lookup: alias -> canonical brand name
        alias_map = {}
        for brand, info in BRAND_MODEL_DB.items():
            alias_map[brand.lower()] = brand
            for alias in info.get("aliases", []):
                alias_map[alias.lower()] = brand

        for _, row in self.df.iterrows():
            title = str(row.get("title", "")).lower()
            url = str(row.get("url", "")).lower()
            existing_brand = str(row.get("brand", "")).strip()
            existing_model = str(row.get("model", "")).strip()

            # Use existing brand if provided and valid
            found_brand = None
            found_model = None

            if existing_brand and existing_brand.lower() in alias_map:
                found_brand = alias_map[existing_brand.lower()]
            else:
                # Search in title and URL
                search_text = f"{title} {url}"
                for alias, canonical in sorted(alias_map.items(), key=lambda x: -len(x[0])):
                    if alias in search_text:
                        found_brand = canonical
                        break

            # Model extraction
            if found_brand:
                if existing_model and existing_model.lower() not in ("nan", "none", ""):
                    # Validate existing model
                    brand_models = BRAND_MODEL_DB.get(found_brand, {}).get("models", [])
                    model_lower = [m.lower() for m in brand_models]
                    if existing_model.lower() in model_lower:
                        idx = model_lower.index(existing_model.lower())
                        found_model = brand_models[idx]
                    else:
                        # Fuzzy match
                        found_model = self._fuzzy_match_model(existing_model, brand_models) or existing_model

                if not found_model:
                    # Search for model in title/URL
                    brand_models = BRAND_MODEL_DB.get(found_brand, {}).get("models", [])
                    for model in sorted(brand_models, key=len, reverse=True):
                        if model.lower() in title or model.lower().replace(" ", "-") in url:
                            found_model = model
                            break

            brands.append(found_brand or "Unknown")
            models.append(found_model or "Unknown")

        self.df["brand"] = brands
        self.df["model"] = models

        # Add brand metadata
        self.df["brand_origin"] = self.df["brand"].map(
            lambda b: BRAND_MODEL_DB.get(b, {}).get("origin", "Unknown")
        )
        self.df["brand_tier"] = self.df["brand"].map(
            lambda b: BRAND_MODEL_DB.get(b, {}).get("tier_default", "Unknown")
        )

        known = self.df[self.df["brand"] != "Unknown"]
        logger.info(f"Brand extraction: {len(known)}/{len(self.df)} identified ({len(known)/len(self.df)*100:.1f}%)")

    @staticmethod
    def _fuzzy_match_model(candidate, model_list, threshold=0.75):
        """Fuzzy match a model name against known models."""
        best_match = None
        best_score = 0
        for model in model_list:
            score = SequenceMatcher(None, candidate.lower(), model.lower()).ratio()
            if score > best_score and score >= threshold:
                best_score = score
                best_match = model
        return best_match

    # ─── STEP 4: Heuristic Enrichment ───

    def _detect_body_type(self):
        """Detect body type from model database and text analysis."""
        def detect(row):
            # Check if already present
            if pd.notna(row.get("body_type")) and row["body_type"] not in ("Unknown", "Nan"):
                return row["body_type"]

            model = str(row.get("model", ""))
            title = str(row.get("title", "")).lower()
            url = str(row.get("url", "")).lower()
            search_text = f"{title} {url}"

            # Check model against known body type mappings
            for body_type, rules in BODY_TYPE_RULES.items():
                if model in rules["models"]:
                    return body_type

            # Check keywords
            for body_type, rules in BODY_TYPE_RULES.items():
                for keyword in rules["keywords"]:
                    if keyword in search_text:
                        return body_type

            return "Unknown"

        self.df["body_type"] = self.df.apply(detect, axis=1)

    def _detect_fuel_type(self):
        """Detect fuel type from brand database and text analysis."""
        ELECTRIC_KEYWORDS = ["electric", "ev", "bev", "zero emission", "e-tron",
                             "eq", "mach-e", "ioniq", "id.", "bz4x"]
        HYBRID_KEYWORDS = ["hybrid", "phev", "plug-in", "e-hybrid", "e-power"]
        DIESEL_KEYWORDS = ["diesel", "tdi", "cdi", "dci", "d4d", "turbodiesel"]

        def detect(row):
            if pd.notna(row.get("fuel_type")) and row["fuel_type"] not in ("Unknown", "Nan"):
                ft = row["fuel_type"].lower()
                if "electric" in ft:
                    return "Electric"
                if "hybrid" in ft:
                    return "Hybrid"
                if "diesel" in ft:
                    return "Diesel"
                if "petrol" in ft or "gasoline" in ft or "gas" in ft:
                    return "Petrol"
                return row["fuel_type"]

            brand = str(row.get("brand", ""))
            brand_info = BRAND_MODEL_DB.get(brand, {})
            if brand_info.get("all_electric"):
                return "Electric"

            title = str(row.get("title", "")).lower()
            model = str(row.get("model", "")).lower()
            search_text = f"{title} {model}"

            if any(kw in search_text for kw in ELECTRIC_KEYWORDS):
                return "Electric"
            if any(kw in search_text for kw in HYBRID_KEYWORDS):
                return "Hybrid"
            if any(kw in search_text for kw in DIESEL_KEYWORDS):
                return "Diesel"

            return "Petrol"  # Default for UAE market

        self.df["fuel_type"] = self.df.apply(detect, axis=1)

    def _detect_transmission(self):
        """Detect transmission type."""
        def detect(row):
            if pd.notna(row.get("transmission")) and row["transmission"] not in ("Unknown", "Nan"):
                t = row["transmission"].lower()
                if "auto" in t:
                    return "Automatic"
                if "manual" in t:
                    return "Manual"
                return row["transmission"]

            title = str(row.get("title", "")).lower()
            if "manual" in title or "mt" in title.split():
                return "Manual"
            return "Automatic"  # 95%+ of UAE market is automatic

        self.df["transmission"] = self.df.apply(detect, axis=1)

    def _detect_specs_origin(self):
        """Detect if GCC spec, American spec, or other import."""
        def detect(row):
            specs = str(row.get("specs", "")).lower()
            title = str(row.get("title", "")).lower()
            url = str(row.get("url", "")).lower()
            search_text = f"{specs} {title} {url}"

            if "gcc" in search_text or "gulf" in search_text:
                return "GCC Spec"
            if "american" in search_text or "us spec" in search_text or "usa" in search_text:
                return "American Spec"
            if "european" in search_text or "eu spec" in search_text:
                return "European Spec"
            if "japanese" in search_text or "japan" in search_text:
                return "Japanese Spec"
            if "korean" in search_text:
                return "Korean Spec"
            if "import" in search_text:
                return "Import"
            return "Unknown"

        self.df["specs_origin"] = self.df.apply(detect, axis=1)

    def _detect_seller_type(self):
        """Detect if dealer or private seller."""
        DEALER_KEYWORDS = ["motors", "auto", "cars", "trading", "showroom",
                           "gallery", "certified", "dealer", "dealership"]

        def detect(row):
            if pd.notna(row.get("seller_type")) and row["seller_type"] not in ("Unknown", "Nan"):
                return row["seller_type"]
            dealer = str(row.get("dealer", row.get("dealer_name", ""))).lower()
            if any(kw in dealer for kw in DEALER_KEYWORDS):
                return "Dealer"
            return "Unknown"

        self.df["seller_type"] = self.df.apply(detect, axis=1)

    # ─── STEP 5: Market Classification ───

    def _classify_price_tier(self):
        """Classify listings into market tiers."""
        def classify(price):
            for tier, bounds in PRICE_TIERS.items():
                if bounds["min"] <= price <= bounds["max"]:
                    return tier
            return "Exotic"

        self.df["price_tier"] = self.df["price"].apply(classify)

    def _calculate_age_and_depreciation(self):
        """Calculate car age and estimated depreciation."""
        current_year = datetime.now().year
        self.df["car_age"] = current_year - self.df["year"]
        self.df.loc[self.df["car_age"] < 0, "car_age"] = np.nan

        # Price per year of age (rough depreciation indicator)
        self.df["price_per_age"] = np.where(
            self.df["car_age"] > 0,
            self.df["price"] / self.df["car_age"],
            np.nan
        )

        # Mileage per year (usage intensity)
        self.df["mileage_per_year"] = np.where(
            self.df["car_age"] > 0,
            self.df["mileage"] / self.df["car_age"],
            np.nan
        )

    # ─── STEP 6: Statistical Cleaning ───

    def _remove_price_outliers(self):
        """Remove statistical outliers using IQR per brand."""
        before = len(self.df)
        clean_frames = []

        for brand in self.df["brand"].unique():
            brand_df = self.df[self.df["brand"] == brand].copy()

            if len(brand_df) >= 10:
                q1 = brand_df["price"].quantile(0.05)
                q3 = brand_df["price"].quantile(0.95)
                iqr = q3 - q1
                lower = q1 - 1.5 * iqr
                upper = q3 + 1.5 * iqr
                brand_df = brand_df[
                    (brand_df["price"] >= max(lower, 3000)) &
                    (brand_df["price"] <= upper)
                ]

            clean_frames.append(brand_df)

        self.df = pd.concat(clean_frames, ignore_index=True)
        logger.info(f"Outlier removal: {before} → {len(self.df)} ({before - len(self.df)} removed)")

    # ─── STEP 7: Smart Deduplication ───

    def _smart_deduplicate(self):
        """Advanced deduplication using content hashing."""
        before = len(self.df)

        # Create fingerprint
        self.df["_fingerprint"] = self.df.apply(
            lambda row: hashlib.md5(
                f"{row.get('brand', '')}|{row.get('model', '')}|{row.get('year', '')}|"
                f"{row.get('price', '')}|{row.get('mileage', '')}".lower().encode()
            ).hexdigest(),
            axis=1
        )

        # When duplicates exist, keep the one with the most data (higher quality)
        self.df["_completeness"] = self.df.notna().sum(axis=1)
        self.df = self.df.sort_values("_completeness", ascending=False)
        self.df = self.df.drop_duplicates(subset="_fingerprint", keep="first")
        self.df = self.df.drop(columns=["_fingerprint", "_completeness"])

        logger.info(f"Deduplication: {before} → {len(self.df)} ({before - len(self.df)} duplicates)")

    # ─── STEP 8: Data Quality Scoring ───

    def _score_data_quality(self):
        """Assign a quality score (0-100) to each listing."""
        WEIGHT_MAP = {
            "brand":        10,
            "model":        10,
            "year":         15,
            "price":        15,
            "mileage":      10,
            "body_type":    5,
            "fuel_type":    5,
            "transmission": 5,
            "location":     5,
            "color":        3,
            "specs_origin": 5,
            "url":          5,
            "seller_type":  3,
            "engine":       4,
        }

        def score(row):
            total = 0
            for field, weight in WEIGHT_MAP.items():
                val = row.get(field)
                if pd.notna(val) and str(val).strip() not in ("Unknown", "", "Nan"):
                    total += weight
            return total

        self.df["quality_score"] = self.df.apply(score, axis=1)

    # ─── STEP 9: Cross-Source Validation ───

    def _cross_source_validation(self):
        """
        Compare prices across Dubizzle and Dubicars for the same brand/model/year.
        Flag listings that are significantly cheaper or more expensive than cross-source median.
        This helps identify suspicious listings or great deals.
        """
        self.df["price_vs_market"] = np.nan
        self.df["cross_source_flag"] = "Normal"

        grouped = self.df.groupby(["brand", "model", "year"])

        for (brand, model, year), group in grouped:
            if len(group) < 3 or brand == "Unknown":
                continue

            median_price = group["price"].median()
            std_price = group["price"].std()

            if std_price == 0 or pd.isna(std_price):
                continue

            for idx in group.index:
                price = self.df.loc[idx, "price"]
                z_score = (price - median_price) / std_price
                self.df.loc[idx, "price_vs_market"] = round(z_score, 2)

                pct_diff = ((price - median_price) / median_price) * 100

                if pct_diff < -30:
                    self.df.loc[idx, "cross_source_flag"] = "Potential Deal 🔥"
                elif pct_diff < -15:
                    self.df.loc[idx, "cross_source_flag"] = "Below Market"
                elif pct_diff > 30:
                    self.df.loc[idx, "cross_source_flag"] = "Overpriced ⚠️"
                elif pct_diff > 15:
                    self.df.loc[idx, "cross_source_flag"] = "Above Market"

        # Cross-source comparison: same car on both platforms
        multi_source = self.df.groupby(["brand", "model", "year"]).filter(
            lambda g: g["source"].nunique() > 1
        )
        if len(multi_source) > 0:
            source_comparison = multi_source.groupby(
                ["brand", "model", "year", "source"]
            )["price"].median().unstack(fill_value=np.nan)

            if "dubizzle" in source_comparison.columns and "dubicars" in source_comparison.columns:
                source_comparison["price_diff_pct"] = (
                    (source_comparison["dubizzle"] - source_comparison["dubicars"])
                    / source_comparison["dubicars"] * 100
                ).round(1)
                self.source_comparison = source_comparison
                logger.info(f"Cross-source validation: {len(source_comparison)} brand/model/year combos compared")

    # ─── Quality Report ───

    def _generate_quality_report(self):
        """Generate a comprehensive quality report."""
        total = len(self.df)
        self.quality_report = {
            "total_listings": total,
            "source_breakdown": self.df["source"].value_counts().to_dict(),
            "brand_coverage": {
                "identified": int((self.df["brand"] != "Unknown").sum()),
                "unknown": int((self.df["brand"] == "Unknown").sum()),
                "pct_identified": round((self.df["brand"] != "Unknown").mean() * 100, 1),
            },
            "model_coverage": {
                "identified": int((self.df["model"] != "Unknown").sum()),
                "pct_identified": round((self.df["model"] != "Unknown").mean() * 100, 1),
            },
            "field_completeness": {
                col: round(self.df[col].notna().mean() * 100, 1)
                for col in ["price", "year", "mileage", "brand", "model",
                            "body_type", "fuel_type", "location", "color"]
                if col in self.df.columns
            },
            "avg_quality_score": round(self.df["quality_score"].mean(), 1),
            "price_stats": {
                "min": float(self.df["price"].min()),
                "max": float(self.df["price"].max()),
                "mean": round(float(self.df["price"].mean()), 2),
                "median": float(self.df["price"].median()),
            },
            "top_brands": self.df[self.df["brand"] != "Unknown"]["brand"]
                .value_counts().head(15).to_dict(),
            "cross_source_flags": self.df["cross_source_flag"].value_counts().to_dict(),
            "extraction_methods": self.df["extraction_method"].value_counts().to_dict()
                if "extraction_method" in self.df.columns else {},
        }

        logger.info(f"Quality Report: {json.dumps(self.quality_report, indent=2, default=str)}")
        return self.quality_report


    # ─── Export Helpers ───

    def export_to_csv(self, path="data/processed_listings.csv"):
        """Export processed data to CSV."""
        self.df.to_csv(path, index=False)
        logger.info(f"Exported {len(self.df)} records to {path}")

    def export_to_excel(self, path="data/uae_car_market.xlsx"):
        """Export to Excel with multiple sheets."""
        import os
        os.makedirs(os.path.dirname(path), exist_ok=True)

        with pd.ExcelWriter(path, engine="openpyxl") as writer:
            # Main data
            self.df.to_excel(writer, sheet_name="All Listings", index=False)

            # Summary by brand
            brand_summary = self.df[self.df["brand"] != "Unknown"].groupby("brand").agg(
                count=("price", "size"),
                avg_price=("price", "mean"),
                median_price=("price", "median"),
                min_price=("price", "min"),
                max_price=("price", "max"),
                avg_mileage=("mileage", "mean"),
                avg_year=("year", "mean"),
                avg_quality=("quality_score", "mean"),
            ).round(0).sort_values("count", ascending=False)
            brand_summary.to_excel(writer, sheet_name="Brand Summary")

            # Deals sheet
            deals = self.df[self.df["cross_source_flag"].str.contains("Deal|Below", na=False)]
            deals = deals.sort_values("price_vs_market")
            deals.to_excel(writer, sheet_name="Best Deals", index=False)

            # Price tier breakdown
            tier_summary = self.df.groupby("price_tier").agg(
                count=("price", "size"),
                avg_price=("price", "mean"),
                top_brand=("brand", lambda x: x.value_counts().index[0] if len(x) > 0 else "N/A"),
            ).round(0)
            tier_summary.to_excel(writer, sheet_name="Market Tiers")

        logger.info(f"Excel export complete: {path}")

    def export_to_json(self, path="data/processed_listings.json"):
        """Export to JSON with metadata."""
        import os
        os.makedirs(os.path.dirname(path), exist_ok=True)

        output = {
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "total_listings": len(self.df),
                "quality_report": self.quality_report,
            },
            "listings": json.loads(self.df.to_json(orient="records", date_format="iso")),
        }

        with open(path, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2, default=str)

        logger.info(f"JSON export complete: {path}")
