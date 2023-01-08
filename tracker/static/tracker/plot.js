const myChart = echarts.init(document.getElementById("main"));
const myData = JSON.parse(document.getElementById("my-data").textContent);
const dates = myData.map(entry => entry.date);
const amounts = myData.map(entry => entry.amount);

var option = {
    title: {
        text: "Amount by Date"
    },
    tooltip: {},
    legend: {
        data: ["Amount"]
    },
    xAxis: {
        data: dates,
    },
    yAxis: {},
    series: [
        {
            name: "Amount",
            type: "bar",
            data: amounts,
        }
    ]
};

myChart.setOption(option);
