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
        tooltip: {},
        legend: {},
        series: {
            type: "pie",
            data: seriesData,
        },
    };
    chart.setOption(option);
}

const data = JSON.parse(document.getElementById("my-data").textContent);
const barChart = echarts.init(document.getElementById("bar-chart"));
const pieChart = echarts.init(document.getElementById("pie-chart"));

configureBarChart(barChart, data);
configurePieChart(pieChart, data);
