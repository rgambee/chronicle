const chart = echarts.init(document.getElementById("main"));
const data = JSON.parse(document.getElementById("my-data").textContent);
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
        text: "Amount by Date"
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
