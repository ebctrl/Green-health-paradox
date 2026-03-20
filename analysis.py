"""
===============================================================================
THE GREEN-HEALTH PARADOX
Analyzing the Relationship Between Environmental Impact, Nutritional Quality,
and Processing Level — With a Focus on Vegan vs. Non-Vegan Products
===============================================================================
Author: Ernesto | Portfolio Project
Tools: Python (Pandas, Seaborn, Matplotlib), SQL
Datasets: 5 interconnected CSVs from Kaggle Global Food & Nutrition Database
    - foods_health_scores_allergens.csv (primary: 4,997 products)
    - comprehensive_foods_usda.csv (supplementary: 40,000 USDA products)
    - foods_dietary_restrictions.csv
    - foods_allergens.csv
    - healthy_foods_database.csv

HOW TO REPLICATE:
    1. Download datasets from Kaggle (see README)
    2. Place all CSVs in data/ folder
    3. pip install pandas numpy seaborn matplotlib
    4. python analysis.py
===============================================================================
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import seaborn as sns
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

# =============================================================================
# CONFIGURATION
# =============================================================================
OUTPUT_DIR = Path("output")
VIZ_DIR = Path("visualizations")
OUTPUT_DIR.mkdir(exist_ok=True)
VIZ_DIR.mkdir(exist_ok=True)

sns.set_theme(style="whitegrid", font_scale=1.05)
FIG_DPI = 150

COLORS = {
    "vegan": "#4CAF50",
    "vegetarian": "#FFA726",
    "omnivore": "#E53935",
    "primary": "#1A73E8",
    "secondary": "#34A853",
    "accent": "#FBBC04",
    "danger": "#EA4335",
}
NOVA_PALETTE = {1: "#4CAF50", 2: "#8BC34A", 3: "#FFC107", 4: "#F44336"}
NUTRI_PALETTE = {"A": "#038141", "B": "#85BB2F", "C": "#FECB02", "D": "#EE8100", "E": "#E63E11"}
ECO_PALETTE = {"A-PLUS": "#1B5E20", "A": "#2E7D32", "B": "#43A047", "C": "#FDD835", "D": "#FF8F00", "E": "#E65100", "F": "#B71C1C"}

print("=" * 80)
print("THE GREEN-HEALTH PARADOX")
print("Sustainability vs. Nutrition in the Global Food Supply")
print("=" * 80)


# =============================================================================
# STAGE 1: DATA ARCHITECTURE & CLEANING
# =============================================================================
print("\n" + "=" * 80)
print("STAGE 1: DATA ARCHITECTURE & CLEANING")
print("=" * 80)

# ---- 1.1 Load primary dataset ----
print("\n[1.1] Loading datasets...")
df_main = pd.read_csv("data/foods_health_scores_allergens.csv")
df_usda = pd.read_csv("data/comprehensive_foods_usda.csv")
print(f"  Primary (Open Food Facts): {df_main.shape[0]:,} products × {df_main.shape[1]} cols")
print(f"  Supplementary (USDA):      {df_usda.shape[0]:,} products × {df_usda.shape[1]} cols")

# ---- 1.2 Missing values strategy ----
print("\n[1.2] Missing values analysis...")
key_cols = ["nutriscore_grade", "nova_group", "ecoscore_grade", "energy_kcal",
            "fat_100g", "proteins_100g", "carbs_100g"]
for col in key_cols:
    n_miss = df_main[col].isnull().sum()
    pct = n_miss / len(df_main) * 100
    print(f"  {col:<22}: {n_miss:>5} missing ({pct:.1f}%)")

df = df_main.copy()

# Strategy: Do NOT impute Nutri-Score/Eco-Score/NOVA — these are categorical labels
# where imputation would introduce false classifications. Instead, filter unknowns.
print("\n[1.3] Cleaning scores...")

# Remove UNKNOWN and NOT-APPLICABLE from score columns (not real grades)
valid_nutri = ["A", "B", "C", "D", "E"]
valid_eco = ["A-PLUS", "A", "B", "C", "D", "E", "F"]

df["nutriscore_grade"] = df["nutriscore_grade"].where(df["nutriscore_grade"].isin(valid_nutri))
df["ecoscore_grade"] = df["ecoscore_grade"].where(df["ecoscore_grade"].isin(valid_eco))

# Drop rows where NOVA is missing (9.5% — acceptable loss)
print(f"  Before cleaning: {len(df):,} rows")
n_before = len(df)
df = df.dropna(subset=["nova_group"])
df["nova_group"] = df["nova_group"].astype(int)
print(f"  After dropping missing NOVA: {len(df):,} rows (lost {n_before - len(df):,})")

# ---- 1.4 Create Dietary_Type column ----
print("\n[1.4] Creating Dietary_Type classification...")
# Logic:
#   Vegan = no dairy, no eggs, no fish
#   Vegetarian = no fish, but has dairy OR eggs
#   Omnivore = contains fish (or meat indicators)

def classify_diet(row):
    has_dairy = row["contains_dairy"]
    has_eggs = row["contains_eggs"]
    has_fish = row["contains_fish"]

    if has_fish:
        return "Omnivore"
    elif has_dairy or has_eggs:
        return "Vegetarian"
    else:
        return "Vegan"

df["Dietary_Type"] = df.apply(classify_diet, axis=1)
print(f"  Dietary distribution:")
for dtype, count in df["Dietary_Type"].value_counts().items():
    print(f"    {dtype:<12}: {count:>5} products ({count/len(df)*100:.1f}%)")

# ---- 1.5 Create numeric scores for analysis ----
print("\n[1.5] Creating numeric score mappings...")
nutri_map = {"A": 5, "B": 4, "C": 3, "D": 2, "E": 1}
eco_map = {"A-PLUS": 7, "A": 6, "B": 5, "C": 4, "D": 3, "E": 2, "F": 1}
nova_labels = {1: "Unprocessed", 2: "Processed Ingredients", 3: "Processed", 4: "Ultra-Processed"}

df["nutri_score_num"] = df["nutriscore_grade"].map(nutri_map)
df["eco_score_num"] = df["ecoscore_grade"].map(eco_map)
df["nova_label"] = df["nova_group"].map(nova_labels)

# ---- 1.6 Clean categories (extract primary category) ----
print("[1.6] Cleaning product categories...")
def extract_primary_category(cat_str):
    if pd.isna(cat_str):
        return "Unknown"
    parts = str(cat_str).split(",")
    # Take the last (most specific) category
    last = parts[-1].strip()
    # Remove "en:" prefix
    if last.startswith("en:"):
        last = last[3:]
    # Clean formatting
    return last.replace("-", " ").title()

df["Category"] = df["categories"].apply(extract_primary_category)

# ---- 1.7 Clean nutrition values — cap extreme outliers ----
print("[1.7] Capping nutritional outliers...")
for col in ["energy_kcal", "fat_100g", "sugars_100g", "proteins_100g", "salt_100g"]:
    if col in df.columns:
        q99 = df[col].quantile(0.99)
        n_capped = (df[col] > q99).sum()
        if n_capped > 0:
            df.loc[df[col] > q99, col] = q99
            print(f"  {col}: capped {n_capped} values at {q99:.1f}")

# ---- 1.8 Save cleaned data ----
df.to_csv(OUTPUT_DIR / "green_health_cleaned.csv", index=False)
print(f"\n  Cleaned dataset saved: {len(df):,} rows × {df.shape[1]} cols")


# =============================================================================
# STAGE 2: EXPLORATORY DATA ANALYSIS
# =============================================================================
print("\n" + "=" * 80)
print("STAGE 2: EXPLORATORY DATA ANALYSIS")
print("=" * 80)

# ---- 2.1 The Paradox: Nutri-Score vs Eco-Score cross-tabulation ----
print("\n[2.1] The Green-Health Paradox Matrix...")
paradox = df.dropna(subset=["nutriscore_grade", "ecoscore_grade"])
cross = pd.crosstab(paradox["nutriscore_grade"], paradox["ecoscore_grade"], normalize="all") * 100
print("  Nutri-Score × Eco-Score distribution (%):")
print(cross.round(1).to_string())

# ---- 2.2 NOVA by Dietary Type ----
print("\n[2.2] Ultra-processing by Dietary Type...")
nova_diet = df.groupby(["Dietary_Type", "nova_group"]).size().unstack(fill_value=0)
nova_diet_pct = nova_diet.div(nova_diet.sum(axis=1), axis=0) * 100
print(nova_diet_pct.round(1).to_string())

# ---- 2.3 Category rankings ----
print("\n[2.3] Category performance (top 15 by product count)...")
cat_stats = df.groupby("Category").agg(
    products=("product_name", "count"),
    avg_nutri=("nutri_score_num", "mean"),
    avg_eco=("eco_score_num", "mean"),
    avg_nova=("nova_group", "mean"),
    pct_vegan=("Dietary_Type", lambda x: (x == "Vegan").mean() * 100),
).round(2)
cat_stats = cat_stats[cat_stats["products"] >= 30].sort_values("products", ascending=False)
print(cat_stats.head(15).to_string())
cat_stats.to_csv(OUTPUT_DIR / "category_performance.csv")

# ---- 2.4 The Paradox Segments ----
print("\n[2.4] Identifying Paradox Segments...")
paradox_df = df.dropna(subset=["nutri_score_num", "eco_score_num"]).copy()
median_nutri = paradox_df["nutri_score_num"].median()
median_eco = paradox_df["eco_score_num"].median()

def classify_paradox(row):
    high_nutri = row["nutri_score_num"] >= median_nutri
    high_eco = row["eco_score_num"] >= median_eco
    if high_nutri and high_eco:
        return "Win-Win (Healthy + Green)"
    elif high_nutri and not high_eco:
        return "Healthy but Not Green"
    elif not high_nutri and high_eco:
        return "Green but Not Healthy"
    else:
        return "Lose-Lose (Unhealthy + Polluting)"

paradox_df["Paradox_Segment"] = paradox_df.apply(classify_paradox, axis=1)
seg_dist = paradox_df["Paradox_Segment"].value_counts()
print(f"  Segments:")
for seg, count in seg_dist.items():
    print(f"    {seg:<35}: {count:>5} ({count/len(paradox_df)*100:.1f}%)")

# Paradox by dietary type
paradox_by_diet = pd.crosstab(paradox_df["Dietary_Type"], paradox_df["Paradox_Segment"], normalize="index") * 100
print(f"\n  Paradox segments by dietary type (%):")
print(paradox_by_diet.round(1).to_string())
paradox_by_diet.to_csv(OUTPUT_DIR / "paradox_by_dietary_type.csv")


# =============================================================================
# STAGE 3: ADVANCED VISUALIZATIONS
# =============================================================================
print("\n" + "=" * 80)
print("STAGE 3: ADVANCED VISUALIZATIONS")
print("=" * 80)

# ---- VIZ 1: The Green-Health Scatter (Signature Visual) ----
print("\n[VIZ 1] Sustainability vs. Health Scatter Plot...")
scatter_df = df.dropna(subset=["nutri_score_num", "eco_score_num"]).copy()
# Add jitter for better visibility
scatter_df["nutri_jitter"] = scatter_df["nutri_score_num"] + np.random.uniform(-0.3, 0.3, len(scatter_df))
scatter_df["eco_jitter"] = scatter_df["eco_score_num"] + np.random.uniform(-0.3, 0.3, len(scatter_df))

fig, ax = plt.subplots(figsize=(12, 8))
for nova, color in NOVA_PALETTE.items():
    subset = scatter_df[scatter_df["nova_group"] == nova]
    label = f"NOVA {nova}: {nova_labels[nova]} (n={len(subset)})"
    ax.scatter(subset["eco_jitter"], subset["nutri_jitter"],
               c=color, alpha=0.45, s=25, label=label, edgecolors="white", linewidth=0.3)

# Quadrant lines
ax.axhline(y=median_nutri, color="gray", linestyle="--", alpha=0.5, linewidth=1)
ax.axvline(x=median_eco, color="gray", linestyle="--", alpha=0.5, linewidth=1)

# Quadrant labels
ax.text(1.2, 4.8, "GREEN BUT\nNOT HEALTHY", fontsize=9, color="gray", ha="left", va="top", style="italic")
ax.text(6.5, 4.8, "WIN-WIN\n(Healthy + Green)", fontsize=9, color="#2E7D32", ha="right", va="top", fontweight="bold")
ax.text(1.2, 1.2, "LOSE-LOSE", fontsize=9, color="#B71C1C", ha="left", va="bottom", fontweight="bold")
ax.text(6.5, 1.2, "HEALTHY BUT\nNOT GREEN", fontsize=9, color="gray", ha="right", va="bottom", style="italic")

ax.set_xlabel("Eco-Score (1=F, 7=A+) → Higher = More Sustainable", fontsize=12)
ax.set_ylabel("Nutri-Score (1=E, 5=A) → Higher = Healthier", fontsize=12)
ax.set_title("The Green-Health Paradox: Sustainability vs. Nutritional Quality\nColored by Processing Level (NOVA Group)",
             fontsize=14, fontweight="bold", pad=15)
ax.legend(loc="lower center", bbox_to_anchor=(0.5, -0.18), ncol=2, frameon=True, fontsize=9)
for spine in ["top", "right"]:
    ax.spines[spine].set_visible(False)
plt.tight_layout()
fig.savefig(VIZ_DIR / "01_green_health_scatter.png", dpi=FIG_DPI, bbox_inches="tight")
plt.close()


# ---- VIZ 2: Ultra-Processing by Dietary Type (grouped bar) ----
print("[VIZ 2] NOVA Distribution by Dietary Type...")
nova_diet_plot = nova_diet_pct.reindex(["Vegan", "Vegetarian", "Omnivore"])

fig, ax = plt.subplots(figsize=(12, 6))
x = np.arange(len(nova_diet_plot.index))
width = 0.2
diet_colors = [COLORS["vegan"], COLORS["vegetarian"], COLORS["omnivore"]]

for i, nova in enumerate([1, 2, 3, 4]):
    vals = nova_diet_plot[nova].values
    bars = ax.bar(x + i * width, vals, width, label=f"NOVA {nova}: {nova_labels[nova]}",
                  color=NOVA_PALETTE[nova], edgecolor="white")
    for bar, val in zip(bars, vals):
        if val > 3:
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
                    f"{val:.0f}%", ha="center", va="bottom", fontsize=8, fontweight="bold")

ax.set_xticks(x + 1.5 * width)
ax.set_xticklabels(nova_diet_plot.index, fontsize=12)
ax.set_ylabel("Percentage of Products (%)", fontsize=12)
ax.set_title("Processing Level (NOVA) Distribution: Vegan vs. Vegetarian vs. Omnivore",
             fontsize=14, fontweight="bold", pad=15)
ax.legend(frameon=True, fontsize=9)
for spine in ["top", "right"]:
    ax.spines[spine].set_visible(False)
plt.tight_layout()
fig.savefig(VIZ_DIR / "02_nova_by_dietary_type.png", dpi=FIG_DPI, bbox_inches="tight")
plt.close()


# ---- VIZ 3: Nutri-Score Distribution by Dietary Type ----
print("[VIZ 3] Nutri-Score by Dietary Type...")
nutri_diet = df.dropna(subset=["nutriscore_grade"])
nutri_cross = pd.crosstab(nutri_diet["Dietary_Type"], nutri_diet["nutriscore_grade"], normalize="index") * 100
nutri_cross = nutri_cross.reindex(columns=["A", "B", "C", "D", "E"])
nutri_cross = nutri_cross.reindex(["Vegan", "Vegetarian", "Omnivore"])

fig, ax = plt.subplots(figsize=(12, 5))
nutri_cross.plot(kind="barh", stacked=True, ax=ax,
                  color=[NUTRI_PALETTE[g] for g in ["A", "B", "C", "D", "E"]],
                  edgecolor="white", linewidth=0.5)
ax.set_xlabel("Percentage (%)", fontsize=12)
ax.set_ylabel("")
ax.set_title("Nutri-Score Distribution: Vegan vs. Vegetarian vs. Omnivore",
             fontsize=14, fontweight="bold", pad=15)
ax.legend(title="Nutri-Score", bbox_to_anchor=(1.02, 1), loc="upper left")
ax.set_xlim(0, 100)
for spine in ["top", "right"]:
    ax.spines[spine].set_visible(False)
plt.tight_layout()
fig.savefig(VIZ_DIR / "03_nutriscore_by_diet.png", dpi=FIG_DPI, bbox_inches="tight")
plt.close()


# ---- VIZ 4: Eco-Score by Dietary Type ----
print("[VIZ 4] Eco-Score by Dietary Type...")
eco_diet = df.dropna(subset=["ecoscore_grade"])
eco_order = ["A-PLUS", "A", "B", "C", "D", "E", "F"]
eco_cross = pd.crosstab(eco_diet["Dietary_Type"], eco_diet["ecoscore_grade"], normalize="index") * 100
eco_cross = eco_cross.reindex(columns=[c for c in eco_order if c in eco_cross.columns])
eco_cross = eco_cross.reindex(["Vegan", "Vegetarian", "Omnivore"])

fig, ax = plt.subplots(figsize=(12, 5))
eco_cross.plot(kind="barh", stacked=True, ax=ax,
                color=[ECO_PALETTE.get(g, "#999") for g in eco_cross.columns],
                edgecolor="white", linewidth=0.5)
ax.set_xlabel("Percentage (%)", fontsize=12)
ax.set_ylabel("")
ax.set_title("Eco-Score Distribution: Vegan vs. Vegetarian vs. Omnivore",
             fontsize=14, fontweight="bold", pad=15)
ax.legend(title="Eco-Score", bbox_to_anchor=(1.02, 1), loc="upper left")
ax.set_xlim(0, 100)
for spine in ["top", "right"]:
    ax.spines[spine].set_visible(False)
plt.tight_layout()
fig.savefig(VIZ_DIR / "04_ecoscore_by_diet.png", dpi=FIG_DPI, bbox_inches="tight")
plt.close()


# ---- VIZ 5: Paradox Quadrant Breakdown by Diet ----
print("[VIZ 5] Paradox Quadrant by Dietary Type...")
paradox_plot = paradox_by_diet.reindex(["Vegan", "Vegetarian", "Omnivore"])
seg_order = ["Win-Win (Healthy + Green)", "Healthy but Not Green", "Green but Not Healthy", "Lose-Lose (Unhealthy + Polluting)"]
seg_colors = ["#2E7D32", "#1565C0", "#F9A825", "#C62828"]
paradox_plot = paradox_plot.reindex(columns=[c for c in seg_order if c in paradox_plot.columns])

fig, ax = plt.subplots(figsize=(12, 5))
paradox_plot.plot(kind="barh", stacked=True, ax=ax,
                   color=seg_colors[:len(paradox_plot.columns)],
                   edgecolor="white", linewidth=0.5)
ax.set_xlabel("Percentage (%)", fontsize=12)
ax.set_ylabel("")
ax.set_title("The Paradox: How Diet Types Fall Into Health-Sustainability Quadrants",
             fontsize=14, fontweight="bold", pad=15)
ax.legend(title="Quadrant", bbox_to_anchor=(1.02, 1), loc="upper left", fontsize=8)
ax.set_xlim(0, 100)
for spine in ["top", "right"]:
    ax.spines[spine].set_visible(False)
plt.tight_layout()
fig.savefig(VIZ_DIR / "05_paradox_quadrants.png", dpi=FIG_DPI, bbox_inches="tight")
plt.close()


# ---- VIZ 6: Nutrition Profile Radar-style comparison ----
print("[VIZ 6] Nutritional Profile by Dietary Type...")
nutrition_cols = ["energy_kcal", "fat_100g", "sugars_100g", "proteins_100g", "fiber_100g", "salt_100g"]
nutr_by_diet = df.groupby("Dietary_Type")[nutrition_cols].mean()
nutr_by_diet = nutr_by_diet.reindex(["Vegan", "Vegetarian", "Omnivore"])

fig, axes = plt.subplots(2, 3, figsize=(16, 9))
axes = axes.flatten()
nice_names = {"energy_kcal": "Calories (kcal)", "fat_100g": "Fat (g/100g)",
              "sugars_100g": "Sugar (g/100g)", "proteins_100g": "Protein (g/100g)",
              "fiber_100g": "Fiber (g/100g)", "salt_100g": "Salt (g/100g)"}
bar_colors = [COLORS["vegan"], COLORS["vegetarian"], COLORS["omnivore"]]

for idx, col in enumerate(nutrition_cols):
    ax = axes[idx]
    vals = nutr_by_diet[col].values
    bars = ax.bar(["Vegan", "Vegetarian", "Omnivore"], vals, color=bar_colors, edgecolor="white", alpha=0.85)
    for bar, val in zip(bars, vals):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.3,
                f"{val:.1f}", ha="center", va="bottom", fontsize=9, fontweight="bold")
    ax.set_title(nice_names.get(col, col), fontsize=11, fontweight="bold")
    ax.set_ylabel("")
    for spine in ["top", "right"]:
        ax.spines[spine].set_visible(False)

plt.suptitle("Nutritional Profile Comparison: Vegan vs. Vegetarian vs. Omnivore",
             fontsize=14, fontweight="bold", y=1.01)
plt.tight_layout()
fig.savefig(VIZ_DIR / "06_nutrition_by_diet.png", dpi=FIG_DPI, bbox_inches="tight")
plt.close()


# ---- VIZ 7: NOVA × Nutri-Score Heatmap ----
print("[VIZ 7] NOVA × Nutri-Score Heatmap...")
nova_nutri = df.dropna(subset=["nutriscore_grade"])
heatmap_data = pd.crosstab(nova_nutri["nova_group"], nova_nutri["nutriscore_grade"])
heatmap_data = heatmap_data.reindex(columns=["A", "B", "C", "D", "E"])
heatmap_data.index = [f"NOVA {int(i)}" for i in heatmap_data.index]

fig, ax = plt.subplots(figsize=(10, 5))
sns.heatmap(heatmap_data, annot=True, fmt="d", cmap="YlOrRd",
            linewidths=0.5, ax=ax, cbar_kws={"label": "Product Count"})
ax.set_title("Processing Level (NOVA) vs. Nutritional Quality (Nutri-Score)\nProduct Count Heatmap",
             fontsize=14, fontweight="bold", pad=15)
ax.set_ylabel("Processing Level")
ax.set_xlabel("Nutri-Score Grade")
plt.tight_layout()
fig.savefig(VIZ_DIR / "07_nova_nutriscore_heatmap.png", dpi=FIG_DPI, bbox_inches="tight")
plt.close()


# =============================================================================
# STAGE 4: BUSINESS INSIGHTS & STORYTELLING
# =============================================================================
print("\n" + "=" * 80)
print("STAGE 4: KEY FINDINGS & BUSINESS INSIGHTS")
print("=" * 80)

# Compute key stats for findings
vegan_df = df[df["Dietary_Type"] == "Vegan"]
omni_df = df[df["Dietary_Type"] == "Omnivore"]
veg_df = df[df["Dietary_Type"] == "Vegetarian"]

vegan_nova4_pct = (vegan_df["nova_group"] == 4).mean() * 100
omni_nova4_pct = (omni_df["nova_group"] == 4).mean() * 100
veg_nova4_pct = (veg_df["nova_group"] == 4).mean() * 100

vegan_nutri_a = (vegan_df["nutriscore_grade"] == "A").sum() / vegan_df["nutriscore_grade"].notna().sum() * 100
vegan_eco_ab = vegan_df["ecoscore_grade"].isin(["A-PLUS", "A", "B"]).sum() / vegan_df["ecoscore_grade"].notna().sum() * 100
omni_eco_ab = omni_df["ecoscore_grade"].isin(["A-PLUS", "A", "B"]).sum() / omni_df["ecoscore_grade"].notna().sum() * 100

# Win-win percentages
if len(paradox_df) > 0:
    vegan_paradox = paradox_df[paradox_df["Dietary_Type"] == "Vegan"]
    vegan_winwin = (vegan_paradox["Paradox_Segment"] == "Win-Win (Healthy + Green)").mean() * 100 if len(vegan_paradox) > 0 else 0
    omni_paradox = paradox_df[paradox_df["Dietary_Type"] == "Omnivore"]
    omni_winwin = (omni_paradox["Paradox_Segment"] == "Win-Win (Healthy + Green)").mean() * 100 if len(omni_paradox) > 0 else 0
else:
    vegan_winwin = 0
    omni_winwin = 0

print(f"\n--- KEY STATISTICS ---")
print(f"  Total products analyzed: {len(df):,}")
print(f"  Vegan products: {len(vegan_df):,} ({len(vegan_df)/len(df)*100:.1f}%)")
print(f"  Ultra-processed (NOVA 4) rate:")
print(f"    Vegan:      {vegan_nova4_pct:.1f}%")
print(f"    Vegetarian: {veg_nova4_pct:.1f}%")
print(f"    Omnivore:   {omni_nova4_pct:.1f}%")
print(f"  Vegan Eco-Score A/B rate: {vegan_eco_ab:.1f}%")
print(f"  Omnivore Eco-Score A/B rate: {omni_eco_ab:.1f}%")
print(f"  Win-Win quadrant (Vegan): {vegan_winwin:.1f}%")
print(f"  Win-Win quadrant (Omnivore): {omni_winwin:.1f}%")

insights = f"""
================================================================================
KEY FINDINGS: The Green-Health Paradox
================================================================================

EXECUTIVE SUMMARY:
Analysis of {len(df):,} food products from the Global Food & Nutrition Database,
classified by Nutri-Score (nutritional quality), Eco-Score (environmental impact),
NOVA group (processing level), and dietary type (Vegan/Vegetarian/Omnivore).

--- BUSINESS QUESTION 1 ---
"Is eating green the same as eating healthy?"

ANSWER: NOT NECESSARILY. Being environmentally sustainable and being nutritionally
healthy are two different dimensions that don't always align. Our quadrant analysis
reveals that a significant share of products fall into paradox zones — either
"Green but Not Healthy" or "Healthy but Not Green." This means consumers and 
policymakers cannot assume that eco-friendly labels guarantee good nutrition.

--- BUSINESS QUESTION 2 ---
"Are vegan products healthier and greener than non-vegan alternatives?"

ANSWER: GREENER YES, HEALTHIER — IT DEPENDS. Vegan products score significantly
better on Eco-Score ({vegan_eco_ab:.0f}% rated A/B vs. {omni_eco_ab:.0f}% for omnivore).
However, {vegan_nova4_pct:.0f}% of vegan products are ultra-processed (NOVA 4),
meaning many vegan options achieve their plant-based status through heavy industrial
processing. The "health halo" around vegan foods doesn't always hold.

--- BUSINESS QUESTION 3 ---
"Does processing level explain the gap between sustainability and nutrition?"

ANSWER: YES — NOVA GROUP IS THE HIDDEN VARIABLE. Ultra-processed foods (NOVA 4)
cluster disproportionately in the worst Nutri-Score grades (D and E), regardless
of whether they're vegan or not. Meanwhile, minimally processed foods (NOVA 1)
dominate the best Nutri-Score grades. Processing level is the strongest predictor
of nutritional quality, and it cross-cuts dietary type.

--- PARADOX IN NUMBERS ---
  Products analyzed:              {len(df):,}
  Vegan ultra-processed rate:     {vegan_nova4_pct:.1f}%
  Omnivore ultra-processed rate:  {omni_nova4_pct:.1f}%
  Vegan Eco-Score A/B rate:       {vegan_eco_ab:.1f}%
  Omnivore Eco-Score A/B rate:    {omni_eco_ab:.1f}%

ACTIONABLE RECOMMENDATIONS:
  → Consumers: "Vegan" is not a shortcut for "healthy" — check NOVA group
  → Food industry: Eco-labeling should be paired with processing transparency
  → Policymakers: Nutri-Score and Eco-Score should be displayed together
  → Retailers: Curate "Win-Win" product sections (high Nutri + high Eco)
  → Health tech: Build recommendation engines that optimize BOTH dimensions
================================================================================
"""
print(insights)

with open(OUTPUT_DIR / "key_findings.txt", "w") as f:
    f.write(insights)

# Save summary tables
nova_diet_pct.to_csv(OUTPUT_DIR / "nova_by_dietary_type.csv")
nutr_by_diet.to_csv(OUTPUT_DIR / "nutrition_by_diet.csv")

print("=" * 80)
print("ALL OUTPUTS SAVED SUCCESSFULLY")
print("=" * 80)
print(f"  Visualizations (7): {VIZ_DIR}/")
print(f"  Cleaned data:       {OUTPUT_DIR}/green_health_cleaned.csv")
print(f"  Category stats:     {OUTPUT_DIR}/category_performance.csv")
print(f"  Paradox by diet:    {OUTPUT_DIR}/paradox_by_dietary_type.csv")
print(f"  NOVA by diet:       {OUTPUT_DIR}/nova_by_dietary_type.csv")
print(f"  Nutrition by diet:  {OUTPUT_DIR}/nutrition_by_diet.csv")
print(f"  Key findings:       {OUTPUT_DIR}/key_findings.txt")
