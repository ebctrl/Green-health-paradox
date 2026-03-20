-- ============================================================================
-- THE GREEN-HEALTH PARADOX — SQL Companion Queries
-- Dataset: Global Food & Nutrition Database (cleaned)
-- Table: global_food_stats
-- ============================================================================

-- ============================================================================
-- 1. RANK CATEGORIES: Average Eco-Score vs Nutri-Score
-- ============================================================================
SELECT 
    Category,
    COUNT(*) AS products,
    ROUND(AVG(nutri_score_num), 2) AS avg_nutri_score,
    ROUND(AVG(eco_score_num), 2) AS avg_eco_score,
    ROUND(AVG(nova_group), 2) AS avg_nova,
    RANK() OVER (ORDER BY AVG(nutri_score_num) DESC) AS nutri_rank,
    RANK() OVER (ORDER BY AVG(eco_score_num) DESC) AS eco_rank,
    RANK() OVER (ORDER BY AVG(nutri_score_num) DESC) - 
        RANK() OVER (ORDER BY AVG(eco_score_num) DESC) AS rank_gap
FROM global_food_stats
WHERE nutri_score_num IS NOT NULL AND eco_score_num IS NOT NULL
GROUP BY Category
HAVING COUNT(*) >= 30
ORDER BY rank_gap DESC;


-- ============================================================================
-- 2. ULTRA-PROCESSED (NOVA 4) RATE: Vegan vs Non-Vegan
-- ============================================================================
SELECT 
    Dietary_Type,
    COUNT(*) AS total_products,
    SUM(CASE WHEN nova_group = 4 THEN 1 ELSE 0 END) AS ultra_processed_count,
    ROUND(
        SUM(CASE WHEN nova_group = 4 THEN 1.0 ELSE 0 END) / COUNT(*) * 100, 1
    ) AS ultra_processed_pct,
    SUM(CASE WHEN nova_group = 1 THEN 1 ELSE 0 END) AS unprocessed_count,
    ROUND(
        SUM(CASE WHEN nova_group = 1 THEN 1.0 ELSE 0 END) / COUNT(*) * 100, 1
    ) AS unprocessed_pct
FROM global_food_stats
GROUP BY Dietary_Type
ORDER BY ultra_processed_pct DESC;


-- ============================================================================
-- 3. TOP 10 "MOST SUSTAINABLE BUT LEAST NUTRITIOUS" CATEGORIES
-- (The Green-Health Paradox categories)
-- ============================================================================
WITH category_scores AS (
    SELECT 
        Category,
        COUNT(*) AS products,
        ROUND(AVG(eco_score_num), 2) AS avg_eco,
        ROUND(AVG(nutri_score_num), 2) AS avg_nutri,
        ROUND(AVG(eco_score_num) - AVG(nutri_score_num), 2) AS paradox_gap
    FROM global_food_stats
    WHERE eco_score_num IS NOT NULL AND nutri_score_num IS NOT NULL
    GROUP BY Category
    HAVING COUNT(*) >= 20
)
SELECT 
    Category,
    products,
    avg_eco,
    avg_nutri,
    paradox_gap,
    RANK() OVER (ORDER BY paradox_gap DESC) AS paradox_rank
FROM category_scores
ORDER BY paradox_gap DESC
LIMIT 10;


-- ============================================================================
-- 4. PARADOX QUADRANT ANALYSIS BY DIETARY TYPE
-- ============================================================================
WITH medians AS (
    SELECT 
        -- Using approximate medians
        AVG(nutri_score_num) AS med_nutri,
        AVG(eco_score_num) AS med_eco
    FROM global_food_stats
    WHERE nutri_score_num IS NOT NULL AND eco_score_num IS NOT NULL
),
classified AS (
    SELECT 
        g.*,
        CASE 
            WHEN g.nutri_score_num >= m.med_nutri AND g.eco_score_num >= m.med_eco 
                THEN 'Win-Win'
            WHEN g.nutri_score_num >= m.med_nutri AND g.eco_score_num < m.med_eco 
                THEN 'Healthy but Not Green'
            WHEN g.nutri_score_num < m.med_nutri AND g.eco_score_num >= m.med_eco 
                THEN 'Green but Not Healthy'
            ELSE 'Lose-Lose'
        END AS paradox_quadrant
    FROM global_food_stats g
    CROSS JOIN medians m
    WHERE g.nutri_score_num IS NOT NULL AND g.eco_score_num IS NOT NULL
)
SELECT 
    Dietary_Type,
    paradox_quadrant,
    COUNT(*) AS products,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (PARTITION BY Dietary_Type), 1) AS pct
FROM classified
GROUP BY Dietary_Type, paradox_quadrant
ORDER BY Dietary_Type, pct DESC;


-- ============================================================================
-- 5. NUTRITIONAL PROFILE COMPARISON BY DIETARY TYPE
-- ============================================================================
SELECT 
    Dietary_Type,
    COUNT(*) AS products,
    ROUND(AVG(energy_kcal), 1) AS avg_calories,
    ROUND(AVG(fat_100g), 1) AS avg_fat,
    ROUND(AVG(sugars_100g), 1) AS avg_sugar,
    ROUND(AVG(proteins_100g), 1) AS avg_protein,
    ROUND(AVG(fiber_100g), 1) AS avg_fiber,
    ROUND(AVG(salt_100g), 2) AS avg_salt
FROM global_food_stats
GROUP BY Dietary_Type
ORDER BY Dietary_Type;


-- ============================================================================
-- 6. NOVA GROUP × NUTRI-SCORE CROSS-TABULATION
-- ============================================================================
SELECT 
    nova_group,
    nova_label,
    COUNT(*) AS total,
    ROUND(AVG(CASE WHEN nutriscore_grade = 'A' THEN 1.0 ELSE 0 END) * 100, 1) AS pct_nutri_A,
    ROUND(AVG(CASE WHEN nutriscore_grade = 'B' THEN 1.0 ELSE 0 END) * 100, 1) AS pct_nutri_B,
    ROUND(AVG(CASE WHEN nutriscore_grade IN ('D', 'E') THEN 1.0 ELSE 0 END) * 100, 1) AS pct_nutri_DE,
    ROUND(AVG(nutri_score_num), 2) AS avg_nutri_score
FROM global_food_stats
WHERE nutriscore_grade IS NOT NULL
GROUP BY nova_group, nova_label
ORDER BY nova_group;


-- ============================================================================
-- 7. WINDOW FUNCTION: Top 5 products per dietary type by Eco-Score
-- ============================================================================
WITH ranked AS (
    SELECT 
        product_name,
        Dietary_Type,
        Category,
        ecoscore_grade,
        nutriscore_grade,
        nova_group,
        eco_score_num,
        nutri_score_num,
        ROW_NUMBER() OVER (
            PARTITION BY Dietary_Type 
            ORDER BY eco_score_num DESC, nutri_score_num DESC
        ) AS eco_rank
    FROM global_food_stats
    WHERE eco_score_num IS NOT NULL AND product_name IS NOT NULL
)
SELECT *
FROM ranked
WHERE eco_rank <= 5
ORDER BY Dietary_Type, eco_rank;


-- ============================================================================
-- 8. ECO-SCORE DISTRIBUTION BY DIETARY TYPE
-- ============================================================================
SELECT 
    Dietary_Type,
    ecoscore_grade,
    COUNT(*) AS products,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (PARTITION BY Dietary_Type), 1) AS pct
FROM global_food_stats
WHERE ecoscore_grade IS NOT NULL
GROUP BY Dietary_Type, ecoscore_grade
ORDER BY Dietary_Type, 
    CASE ecoscore_grade 
        WHEN 'A-PLUS' THEN 1 WHEN 'A' THEN 2 WHEN 'B' THEN 3 
        WHEN 'C' THEN 4 WHEN 'D' THEN 5 WHEN 'E' THEN 6 WHEN 'F' THEN 7 
    END;
