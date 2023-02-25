new Tabulator(
    "#entry-table",
    {
        responsiveLayout: "hide",
        columns: [
            {
                title: "Date",
                responsive: 10,
                formatter: "datetime",
                formatterParams:{
                    inputFormat:"yyyy-MM-dd",
                    outputFormat:"DD",
                },
            },
            {
                title: "Amount",
                sorter: "number",
                responsive: 10,
            },
            {
                title: "Category",
                responsive: 20,
                formatter: "html",
            },
            {
                title: "Tags",
                responsive: 30,
            },
            {
                title: "Comment",
                responsive: 40,
            },
            {
                title: "Edit",
                responsive: 50,
                formatter: "html",
            },
            {
                title: "Delete",
                responsive: 50,
                formatter: "html",
            },
        ],
    },
);
