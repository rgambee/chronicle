const chart = echarts.init(document.getElementById("main"));
const data = JSON.parse(document.getElementById("my-data").textContent);
const series = [];
for (const [cat, dateObj] of Object.entries(data)) {
    series.push({
        name: cat,
        type: "bar",
        data: Object.entries(dateObj),
    });
}

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
