// This script expects to be given data in the form of an array of objects. The content
// of each object is defined by tracker.view_utils.SerializableEntry. For convenience,
// here are the properties and their types:
//      * timestamp_ms: Number
//      * amount: Number
//      * category: String


function getFontFamily(element) {
    return window.getComputedStyle(element).getPropertyValue("font-family");
}

function makeDateFormatter(month = "long", day="numeric") {
    return (timestamp) => {
        return new Date(timestamp).toLocaleDateString(
            undefined,
            {
                month: month,
                day: day,
            },
        );
    };
}

// Convert array of objects to a map with the given property as the key
function aggregateData(data, keyName) {
    const aggregated = new Map();
    for (const entry of data) {
        const key = entry[keyName];
        if (!aggregated.has(key)) {
            aggregated.set(key, []);
        }
        // Copy entry without the aggregation key
        const newEntry = Object.keys(entry).reduce(
            (newEntry, key) => {
                if (key !== keyName) {
                    newEntry[key] = entry[key];
                }
                return newEntry;
            },
            {},
        );
        aggregated.get(key).push(newEntry);
    }
    return aggregated;
}

// Add the amounts of entries with the same timestamp and category
function combineAmounts(data) {
    const combined = [];
    const aggregatedByTimestamp = aggregateData(data, "timestamp_ms");
    for (const [timestamp, categoriesAndAmounts] of aggregatedByTimestamp.entries()) {
        const aggregatedByCategory = aggregateData(
            categoriesAndAmounts, "category",
        );
        for (const [category, amounts] of aggregatedByCategory.entries()) {
            const total = amounts.reduce((acc, obj) => acc + obj.amount, 0);
            combined.push(
                {
                    // eslint-disable-next-line camelcase
                    timestamp_ms: timestamp,
                    amount: total,
                    category: category,
                },
            );
        }
    }
    return combined;
}

function initBarChart(element, data) {
    const series = [];
    // Map of category => {timestamp, amount}
    const aggregatedByCategory = aggregateData(data, "category");
    // Map of timestamp => {category, amount}
    const aggregatedByTimestamp = aggregateData(data, "timestamp_ms");
    for (const [category, timesAndAmounts] of aggregatedByCategory.entries()) {
        series.push({
            name: category,
            type: "bar",
            data: timesAndAmounts.map(obj => [obj.timestamp_ms, obj.amount]),
        });
    }
    // Sort series by category name
    series.sort((a, b) => a.name > b.name);

    // Array of [timestamp, totalAmount]
    const dailyTotals = [];
    for (const [timestamp, categoriesAndAmounts] of aggregatedByTimestamp.entries()) {
        // Add up the amounts for this timestamp across all categories
        const total = categoriesAndAmounts.reduce(
            (acc, obj) => acc + obj.amount,
            0,
        );
        dailyTotals.push([timestamp, total]);
    }
    // Sort by timestamp
    dailyTotals.sort((pairA, pairB) => pairA[0] - pairB[0]);
    series.push({
        name: "Daily Total",
        type: "line",
        data: dailyTotals,
    });

    const option = {
        textStyle: {
            fontFamily: getFontFamily(element),
        },
        title: {
            text: "Amount by Date",
        },
        tooltip: {},
        legend: {
            left: "25%",
        },
        dataZoom: {
            type: "slider",
            labelFormatter: makeDateFormatter("short"),
        },
        xAxis: {
            type: "time",
            name: "Date",
        },
        yAxis: {
            type: "value",
            name: "Amount",
        },
        series: series,
    };
    const chart = echarts.init(element);
    chart.setOption(option);
    return chart;
}

function initPieChart(element, data) {
    const aggregatedByCategory = aggregateData(data, "category");
    // Array of {category, totalAmount}
    const seriesData = [];
    for (const [category, timesAndAmounts] of aggregatedByCategory.entries()) {
        // Add up the amounts for this category across all timestamps
        const total = timesAndAmounts.reduce(
            (acc, obj) => acc + obj.amount,
            0,
        );
        seriesData.push({name: category, value: total});
    }
    // Sort seriesData by category name
    seriesData.sort((a, b) => a.name > b.name);

    const option = {
        textStyle: {
            fontFamily: getFontFamily(element),
        },
        title: {
            text: "Amount Breakdown",
        },
        tooltip: {
            formatter: "<strong>{b}:</strong> {c} ({d}%)",
        },
        legend: {
            left: "30%",
        },
        series: {
            type: "pie",
            center: ["50%", "55%"],
            label: {
                formatter: "{bold|{b}}\n{c} ({d}%)",
                rich: {
                    bold: {
                        fontWeight: "bold",
                    },
                },
            },
            data: seriesData,
        },
    };
    const chart = echarts.init(element);
    chart.setOption(option);
    return chart;
}

function initCalendarHeatmap(element, data) {
    // Map of timestamp => {category, amount}
    const aggregatedByTimestamp = aggregateData(data, "timestamp_ms");
    // Include total for each timestamp as well as the per-category amounts
    const totalKey = "_total";
    for (const [timestamp, categoriesAndAmounts] of aggregatedByTimestamp.entries()) {
        const total = categoriesAndAmounts.reduce(
            (acc, obj) => acc + obj.amount,
            0,
        );
        aggregatedByTimestamp.get(timestamp)[totalKey] = total;
    }

    // Convert map to array of [timestamp, totalAmount] pairs for displaying
    const dailyTotals = Array.from(
        aggregatedByTimestamp,
        ([timestamp, categoriesAndAmounts]) => [timestamp, categoriesAndAmounts[totalKey]],
    );
    // Sort by timestamp
    dailyTotals.sort((pairA, pairB) => pairA[0] - pairB[0]);

    let end = new Date();
    if (dailyTotals.length > 0) {
        end = new Date(dailyTotals.at(-1).at(0));
    }
    // Round to end of week (here assumed to stop on Saturday)
    end.setDate(end.getDate() + (6 - end.getDay()));
    // Set start to be at least N weeks earlier
    const spanWeeks = 28;
    // Subtract 1 day since we want to start on a different day of the week
    // than we end on, e.g. Sunday to Saturday.
    const spanMilliseconds = (spanWeeks * 7 - 1) * 24 * 60 * 60 * 1000;
    const start = new Date(end.getTime() - spanMilliseconds);

    const formatDate = makeDateFormatter();
    const option = {
        title: {
            text: "Amount Breakdown",
        },
        textStyle: {
            fontFamily: getFontFamily(element),
        },
        tooltip: {
            formatter: params => {
                const timestamp = params.data[0];
                const tooltipInfo = [[
                    formatDate(timestamp),
                ]];
                if (aggregatedByTimestamp.has(timestamp)) {
                    aggregatedByTimestamp.get(timestamp).forEach(
                        (categoryAndAmount) => {
                            if (categoryAndAmount.category !== totalKey) {
                                tooltipInfo.push(
                                    [
                                        categoryAndAmount.category,
                                        ": ", categoryAndAmount.amount.toString(),
                                    ],
                                );
                            }
                        },
                    );
                }
                // Join each line with "", then join all the lines with breaks
                return tooltipInfo.map(line => line.join("")).join("<br/>");
            },
        },
        calendar: {
            range: [start, end],
        },
        visualMap: {
            show: false,
            min: 0,
            max: Math.max(...dailyTotals.map(tsAndTotal => tsAndTotal[1])),
        },
        series: {
            type: "heatmap",
            coordinateSystem: "calendar",
            data: dailyTotals,
            label: {
                show: true,
                formatter: params => params.data[1].toString(),
            },
        },
    };
    const chart = echarts.init(element);
    chart.setOption(option);
    return chart;
}

const data = combineAmounts(
    JSON.parse(document.getElementById("tracker-data").textContent),
);
const barChartElem = document.getElementById("bar-chart");
const pieChartElem = document.getElementById("pie-chart");
const heatmapChartElem = document.getElementById("heatmap-chart");
initBarChart(barChartElem, data);
initPieChart(pieChartElem, data);
initCalendarHeatmap(heatmapChartElem, data);
