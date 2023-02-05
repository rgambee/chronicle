function configureBarChart(chart, data) {
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
        title: {
            text: "Amount by Date",
        },
        tooltip: {},
        legend: {},
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

    chart.setOption(option);
}

function configurePieChart(chart, data) {
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
        title: {
            text: "Amount Breakdown",
        },
        tooltip: {
            formatter: "<strong>{b}:</strong> {c} ({d}%)",
        },
        legend: {},
        series: {
            type: "pie",
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
    chart.setOption(option);
}

function configureCalendarHeatmap(chart, dataByCategory) {
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

    const option = {
        tooltip: {
            formatter: params => {
                const date = params.data[0];
                const tooltipInfo = [[
                    new Date(date).toLocaleDateString(
                        undefined,
                        {
                            month: "long",
                            day: "numeric",
                        },
                    ),
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
    chart.setOption(option);
}

const data = JSON.parse(document.getElementById("my-data").textContent);
const barChart = echarts.init(document.getElementById("bar-chart"));
const pieChart = echarts.init(document.getElementById("pie-chart"));
const heatmapChart = echarts.init(document.getElementById("heatmap-chart"));

configureBarChart(barChart, data);
configurePieChart(pieChart, data);
configureCalendarHeatmap(heatmapChart, data);
