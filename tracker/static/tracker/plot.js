const chart = echarts.init(document.getElementById("main"));
const data = JSON.parse(document.getElementById("my-data").textContent);
let series = [];
for (const [cat, date_obj] of Object.entries(data)) {
    series.push({
        name: cat,
        type: "bar",
        data: Object.entries(date_obj),
    });
}

var option = {
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
