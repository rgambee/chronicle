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
        data: Array.from(dateTotals),
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

function configureCalendarHeatmap(chart, data) {
    const dateTotals = new Map();
    for (const dateObj of Object.values(data)) {
        for (const [date, amount] of Object.entries(dateObj)) {
            if (!dateTotals.has(date)) {
                dateTotals.set(date, 0);
            }
            dateTotals.set(date, dateTotals.get(date) + amount);
        }
    }
    const dataArray = Array.from(dateTotals).sort();

    const option = {
        tooltip: {},
        calendar: {
            range: [dataArray.at(0).at(0), dataArray.at(-1).at(0)],
        },
        visualMap: {
            show: false,
            min: 0,
            max: Math.max(...dateTotals.values()),
        },
        series: {
            type: "heatmap",
            coordinateSystem: "calendar",
            data: dataArray,
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
