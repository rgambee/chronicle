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

// Sum the `amount` property of an array of objects
function sumAmounts(arrayOfObjects) {
    return arrayOfObjects.reduce(
        (acc, obj) => acc + obj.amount,
        0,
    );
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
            const total = sumAmounts(amounts);
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
    const allCategories = new Set(aggregateData(data, "category").keys());

    // Map of timestamp => [{category, amount}]
    const aggregatedByTimestamp = aggregateData(data, "timestamp_ms");
    const startDate = new Date(Math.min(...aggregatedByTimestamp.keys()));
    const endDate = new Date(Math.max(...aggregatedByTimestamp.keys()));

    // Map of category => [[timestamp, amount]]
    const seriesMap = new Map();
    for (const category of allCategories) {
        seriesMap.set(category, []);
    }

    // Set up moving average calculation
    const averageWindow = 2 * 7;  // 2 weeks == 14 days
    const recentAmounts = (new Array(averageWindow)).fill(0);
    // Array of [timestamp, averageAmount]
    const averages = [];

    // Use Date objects to easily increment one day at a time
    for (let d = new Date(startDate); d <= endDate; d.setDate(d.getDate() + 1)) {
        const timestamp = d.getTime();
        // Initialize each category's amount for this date to 0
        for (const category of allCategories) {
            seriesMap.get(category).push([timestamp, 0]);
        }
        let totalAmountForDate = 0;
        for (const {category, amount} of aggregatedByTimestamp.get(timestamp) || []) {
            if (category === undefined || amount === undefined) {
                continue;
            }
            // For this date (which is the last element in this category's array),
            // increment the amount (which is the second element)
            seriesMap.get(category).at(-1)[1] += amount;
            totalAmountForDate += amount;
        }

        // Update moving average
        recentAmounts.push(totalAmountForDate);
        recentAmounts.shift();
        const avg = recentAmounts.reduce((a, b) => a + b) / recentAmounts.length;
        averages.push([timestamp, avg]);
    }

    const series = [];
    seriesMap.forEach((datesAndAmounts, category) => {
        series.push({
            name: category,
            type: "bar",
            data: datesAndAmounts,
            stack: "group1",
        });
    });
    // Sort series by category name
    series.sort((a, b) => a.name > b.name);

    series.push({
        name: "2 Week Avg",
        type: "line",
        symbol: "none",
        data: averages,
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
            left: "40%",
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
        const total = sumAmounts(timesAndAmounts);
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
            left: "40%",
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
        const total = sumAmounts(categoriesAndAmounts);
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
    // Set end time to noon to avoid ambiguities when crossing daylight saving
    // boundaries. If we leave it at midnight, we could calculate the start date as one
    // day before the one we want if the clocks have moved forward (spring DTS
    // transition) between the start and end dates.
    end.setHours(12);
    // Set start to be at least N weeks earlier
    const spanWeeks = 14;
    // Subtract 1 day since we want to start on a different day of the week
    // than we end on, e.g. Sunday to Saturday.
    const spanMilliseconds = (spanWeeks * 7 - 1) * 24 * 60 * 60 * 1000;
    const start = new Date(end.getTime() - spanMilliseconds);

    // Remove entries before the start date. Otherwise, they'll get stacked in the
    // corner, which looks ugly.
    while (dailyTotals[0][0] < start.getTime()) {
        dailyTotals.shift();
    }

    const formatDate = makeDateFormatter();
    const option = {
        title: {
            text: "Activity Heat Map",
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
            cellSize: 40,
        },
        visualMap: {
            type: "continuous",
            show: false,
            min: 0,
            max: Math.max(...dailyTotals.map(tsAndTotal => tsAndTotal[1])),
            inRange: {
                color: [
                    "#f1f1f1",
                    "#dfe6ef",
                    "#cddbed",
                    "#bcd0ea",
                    "#abc5e7",
                    "#9bbbe1",
                    "#8db0d8",
                    "#81a5ce",
                    "#759ac4",
                    "#6690bc",
                    "#5486b7",
                    "#3d7cb2",
                ],
            },
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
