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

function initBarChart(element, data) {
    const series = [];
    const dateTotals = new Map();
    for (const [cat, dateObj] of Object.entries(data)) {
        series.push({
            name: cat,
            type: "bar",
            data: Object.entries(dateObj),
        });
        for (const [date, amount] of Object.entries(dateObj)) {
            if (!dateTotals.has(date)) {
                dateTotals.set(date, 0);
            }
            dateTotals.set(date, dateTotals.get(date) + amount);
        }
    }

    series.push({
        name: "Daily Total",
        type: "line",
        data: Array.from(dateTotals).sort(),
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
    const categoryTotals = new Map();
    for (const [cat, dateObj] of Object.entries(data)) {
        categoryTotals.set(cat, 0);
        for (const amount of Object.values(dateObj)) {
            categoryTotals.set(cat, categoryTotals.get(cat) + amount);
        }
    }
    const seriesData = [];
    categoryTotals.forEach((value, key) => seriesData.push({name: key, value: value}));

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

function initCalendarHeatmap(element, dataByCategory) {
    // dataByCategory maps category -> date -> amount.
    // Rearrange it to be date -> category -> amount.
    const dataByDate = new Map();
    const totalKey = "_total";
    for (const [category, dateToAmount] of Object.entries(dataByCategory)) {
        for (const [date, amount] of Object.entries(dateToAmount)) {
            if (!dataByDate.has(date)) {
                dataByDate.set(date, new Map());
            }
            const categoryToAmount = dataByDate.get(date);
            if (!categoryToAmount.has(category)) {
                categoryToAmount.set(category, 0);
            }
            categoryToAmount.set(category, categoryToAmount.get(category) + amount);
            // Also sum the total amount for this date
            if (!categoryToAmount.has(totalKey)) {
                categoryToAmount.set(totalKey, 0);
            }
            categoryToAmount.set(totalKey, categoryToAmount.get(totalKey) + amount);
        }
    }

    // Convert map to array of [date, totalAmount] pairs for plotting
    const dateTotals = Array.from(
        dataByDate,
        ([date, categoryToAmount]) => [date, categoryToAmount.get(totalKey)],
    ).sort();

    let start = new Date();
    let end = new Date();
    if (dateTotals.length > 0) {
        start = new Date(dateTotals.at(0).at(0));
        end = new Date(dateTotals.at(-1).at(0));
    }
    // Round to beginning of week (here assumed to start on Sunday)
    start.setDate(start.getDate() - start.getDay());
    // Set end to be at least N weeks later
    const minWeeks = 4;
    end = new Date(
        Math.max(end, new Date(start.getTime() + minWeeks * 7 * 24 * 60 * 60 * 1000)),
    );
    // Round to end of week (here assumed to stop on Saturday)
    end.setDate(end.getDate() + (6 - end.getDay()));

    const formatDate = makeDateFormatter();

    const option = {
        textStyle: {
            fontFamily: getFontFamily(element),
        },
        tooltip: {
            formatter: params => {
                const date = params.data[0];
                const tooltipInfo = [[
                    formatDate(date),
                ]];
                if (dataByDate.has(date)) {
                    dataByDate.get(date).forEach(
                        (amount, category) => {
                            if (category !== totalKey) {
                                tooltipInfo.push([category, ": ", amount.toString()]);
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
            max: Math.max(...dateTotals.map(dateAndTotal => dateAndTotal[1])),
        },
        series: {
            type: "heatmap",
            coordinateSystem: "calendar",
            data: dateTotals,
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

const data = JSON.parse(document.getElementById("tracker-data").textContent);
const barChartElem = document.getElementById("bar-chart");
const pieChartElem = document.getElementById("pie-chart");
const heatmapChartElem = document.getElementById("heatmap-chart");
initBarChart(barChartElem, data);
initPieChart(pieChartElem, data);
initCalendarHeatmap(heatmapChartElem, data);
