"""Statistics tool module — demonstrates data analysis tools.

These tools show how to build analytical tools that accept data as
input and return computed results.  In a real MCP, these would query
a database; here they operate on inline data for portability.
"""

import json
import math

from fastmcp import FastMCP


def register(mcp: FastMCP) -> None:
    """Register statistics tools with the MCP server."""

    @mcp.tool()
    def descriptive_stats(values: list[float]) -> str:
        """Compute descriptive statistics for a list of numbers.

        Args:
            values: A list of numeric values (at least 1 element).
        """
        if not values:
            return json.dumps({"error": "Empty values list"})

        n = len(values)
        mean = sum(values) / n
        sorted_v = sorted(values)
        median = (
            sorted_v[n // 2]
            if n % 2 == 1
            else (sorted_v[n // 2 - 1] + sorted_v[n // 2]) / 2
        )
        variance = sum((x - mean) ** 2 for x in values) / max(n - 1, 1)
        std_dev = math.sqrt(variance)

        return json.dumps({
            "count": n,
            "mean": round(mean, 4),
            "median": round(median, 4),
            "std_dev": round(std_dev, 4),
            "min": min(values),
            "max": max(values),
            "range": round(max(values) - min(values), 4),
        })

    @mcp.tool()
    def percentile(values: list[float], p: float) -> str:
        """Compute the p-th percentile of a list of numbers.

        Args:
            values: A list of numeric values.
            p: Percentile to compute (0-100).
        """
        if not values:
            return json.dumps({"error": "Empty values list"})
        if not 0 <= p <= 100:
            return json.dumps({"error": "Percentile must be between 0 and 100"})

        sorted_v = sorted(values)
        k = (len(sorted_v) - 1) * (p / 100)
        f = math.floor(k)
        c = math.ceil(k)
        if f == c:
            result = sorted_v[int(k)]
        else:
            result = sorted_v[f] * (c - k) + sorted_v[c] * (k - f)

        return json.dumps({
            "percentile": p,
            "value": round(result, 4),
            "count": len(values),
        })

    @mcp.tool()
    def correlation(x: list[float], y: list[float]) -> str:
        """Compute Pearson correlation coefficient between two series.

        Args:
            x: First series of numeric values.
            y: Second series of numeric values (same length as x).
        """
        if len(x) != len(y):
            return json.dumps({"error": "x and y must have the same length"})
        n = len(x)
        if n < 2:
            return json.dumps({"error": "Need at least 2 data points"})

        mean_x = sum(x) / n
        mean_y = sum(y) / n
        cov = sum((xi - mean_x) * (yi - mean_y) for xi, yi in zip(x, y)) / (n - 1)
        std_x = math.sqrt(sum((xi - mean_x) ** 2 for xi in x) / (n - 1))
        std_y = math.sqrt(sum((yi - mean_y) ** 2 for yi in y) / (n - 1))

        if std_x == 0 or std_y == 0:
            return json.dumps({"error": "Zero variance in one or both series"})

        r = cov / (std_x * std_y)
        return json.dumps({
            "pearson_r": round(r, 6),
            "r_squared": round(r ** 2, 6),
            "n": n,
            "interpretation": (
                "strong" if abs(r) >= 0.7
                else "moderate" if abs(r) >= 0.4
                else "weak"
            ),
        })
