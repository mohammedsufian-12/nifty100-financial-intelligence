-- Query 1: Number of companies
SELECT COUNT(*) AS total_companies
FROM companies;


-- Query 2: Companies by sector
SELECT
    s.broad_sector,
    COUNT(*) AS company_count
FROM sectors s
GROUP BY s.broad_sector
ORDER BY company_count DESC;


-- Query 3: Top 10 companies by latest market capitalization
SELECT
    c.company_name,
    m.year,
    m.market_cap_crore
FROM market_cap m
JOIN companies c
    ON c.id = m.company_id
WHERE m.year = (
    SELECT MAX(year)
    FROM market_cap
)
ORDER BY m.market_cap_crore DESC
LIMIT 10;


-- Query 4: Top 10 companies by latest net profit
SELECT
    c.company_name,
    p.year,
    p.net_profit
FROM profit_loss p
JOIN companies c
    ON c.id = p.company_id
WHERE p.year = (
    SELECT MAX(year)
    FROM profit_loss
)
ORDER BY p.net_profit DESC
LIMIT 10;


-- Query 5: Top 10 companies by latest ROE
SELECT
    c.company_name,
    f.year,
    f.return_on_equity_pct
FROM financial_ratios f
JOIN companies c
    ON c.id = f.company_id
WHERE f.year = (
    SELECT MAX(year)
    FROM financial_ratios
)
ORDER BY f.return_on_equity_pct DESC
LIMIT 10;


-- Query 6: Companies with debt-to-equity below 1
SELECT
    c.company_name,
    f.year,
    f.debt_to_equity
FROM financial_ratios f
JOIN companies c
    ON c.id = f.company_id
WHERE f.year = (
    SELECT MAX(year)
    FROM financial_ratios
)
AND f.debt_to_equity < 1
ORDER BY f.debt_to_equity;


-- Query 7: Companies with highest operating profit margin
SELECT
    c.company_name,
    f.year,
    f.operating_profit_margin_pct
FROM financial_ratios f
JOIN companies c
    ON c.id = f.company_id
WHERE f.year = (
    SELECT MAX(year)
    FROM financial_ratios
)
ORDER BY f.operating_profit_margin_pct DESC
LIMIT 10;


-- Query 8: Sector-wise average ROE
SELECT
    s.broad_sector,
    AVG(f.return_on_equity_pct) AS average_roe
FROM financial_ratios f
JOIN sectors s
    ON s.company_id = f.company_id
WHERE f.year = (
    SELECT MAX(year)
    FROM financial_ratios
)
GROUP BY s.broad_sector
ORDER BY average_roe DESC;


-- Query 9: Companies with positive free cash flow
SELECT
    c.company_name,
    f.year,
    f.free_cash_flow_cr
FROM financial_ratios f
JOIN companies c
    ON c.id = f.company_id
WHERE f.year = (
    SELECT MAX(year)
    FROM financial_ratios
)
AND f.free_cash_flow_cr > 0
ORDER BY f.free_cash_flow_cr DESC
LIMIT 10;


-- Query 10: Companies with highest interest coverage
SELECT
    c.company_name,
    f.year,
    f.interest_coverage
FROM financial_ratios f
JOIN companies c
    ON c.id = f.company_id
WHERE f.year = (
    SELECT MAX(year)
    FROM financial_ratios
)
ORDER BY f.interest_coverage DESC
LIMIT 10;