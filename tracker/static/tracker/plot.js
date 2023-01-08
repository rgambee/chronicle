const myChart = echarts.init(document.getElementById("main"));
const myData = JSON.parse(document.getElementById("my-data").textContent);
const date_and_amount = myData.map(entry => [entry.datetime_iso, entry.amount]);

var option = {
    title: {
        text: "Amount by Date"
    },
    tooltip: {},
    legend: {
        data: ["Amount"]
    },
    xAxis: {
        type: "time",
        name: "Date",
    },
    yAxis: {
        name: "Amount",
    },
    series: [
        {
            name: "Amount",
            type: "bar",
            data: date_and_amount,
        }
    ]
};

myChart.setOption(option);
