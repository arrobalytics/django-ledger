import Axios, {AxiosInstance, AxiosRequestConfig, AxiosResponse} from "axios";
import {Chart, ChartItem, ChartOptions} from "chart.js/auto";

function currencyFormatter(value: number): string {
    return Intl.NumberFormat(
        'en-US',
        {
            style: 'currency',
            currency: 'USD'
        })
        .format(value);
}


interface DjangoLedgerJSONDataResponse {
    results: object
}

class BaseChart {

    selector: string;
    chart: Chart | undefined;
    chartData: DjangoLedgerJSONDataResponse | undefined;
    http: AxiosInstance | undefined;
    entitySlug: string;
    consoleLogData: boolean = false;
    lazyGetData: boolean = false;
    fromDate: string | null
    toDate: string | null
    htmlElement: HTMLHtmlElement | null = null

    constructor(selector: string,
                entitySlug: string,
                fromDate: string | null,
                toDate: string | null,
                chartData = undefined) {


        this.selector = selector
        this.fromDate = fromDate
        this.toDate = toDate
        this.getHTMLElement()

        if (!chartData) {
            this.startHttpClient()
        } else {
            this.chartData = chartData
        }

        this.entitySlug = entitySlug;
    }

    getHTMLElement() {
        this.htmlElement = <HTMLHtmlElement>document.getElementById(this.selector)
    }

    getEndPoint(): string | undefined {
        return this.htmlElement!.dataset.endpoint
    }

    getChartData() {
        if (!this.chartData && this.htmlElement) {
            let axiosConfig: AxiosRequestConfig = {
                params: {
                    fromDate: this.fromDate ? this.fromDate : null,
                    toDate: this.toDate ? this.toDate : null,
                }
            }
            this.http?.get(
                <string>this.getEndPoint(), axiosConfig
            ).then((r: AxiosResponse<DjangoLedgerJSONDataResponse>) => {
                this.chartData = r.data;
                if (this.consoleLogData) {
                    console.log(r);
                }
                this.renderChart()
            })
        } else {
            this.renderChart()
        }
    }

    startHttpClient() {
        this.http = Axios.create({})
        if (!this.lazyGetData) {
            this.getChartData()
        }
    }

    renderChart() {
    }

}

class PnLChart extends BaseChart {


    renderChart() {

        if (this.chartData) {
            // @ts-ignore
            let entityName = this.chartData.results['entity_name']
            // @ts-ignore
            let incExpData = this.chartData.results['pnl_data']
            let chartLabels = Object.keys(incExpData);
            let income = chartLabels.map(k => {
                // @ts-ignore
                return incExpData[k]['GROUP_INCOME']
            })
            let expenses = chartLabels.map(k => {
                // @ts-ignore
                return incExpData[k]['GROUP_EXPENSES']
            })

            let data = {
                labels: chartLabels,
                datasets: [
                    {
                        label: 'Income',
                        backgroundColor: 'rgb(70,160,45)',
                        borderColor: 'rgb(115,255,99)',
                        data: income
                    },
                    {
                        label: 'Expenses',
                        backgroundColor: 'rgb(231,46,75)',
                        borderColor: 'rgb(255, 99, 132)',
                        data: expenses
                    }]
            };


            // let tooltipOptions: TooltipOptions = {
            //     callbacks: {
            //         label(
            //             tooltipItem: Chart.ChartTooltipItem,
            //             data: Chart.ChartData): string | string[] {
            //
            //             // @ts-ignore
            //             let dataSet = data.datasets[tooltipItem.datasetIndex];
            //             let tooltipLabelIndex = tooltipItem.index;
            //             let value = dataSet.data[tooltipLabelIndex];
            //
            //             return `${dataSet.label}: ${currencyFormatter(value)}`;
            //
            //         }
            //     }
            // }


            // @ts-ignore
            const ctx = document.getElementById(this.selector) as ChartItem
            let chartOptions: ChartOptions = {

                plugins: {
                    title: {
                        display: true,
                        text: `${entityName} - Income & Expenses`,
                        font: {
                            size: 20
                        }
                    },
                    tooltip: {
                        callbacks: {
                            // label(tooltipItem: TooltipItem<any>): string | string[] | void {
                            //     let dataSet = tooltipItem.dataset[tooltipItem.datasetIndex]
                            //     let tooltipLabelIndex = tooltipItem.dataIndex;
                            //     let value = dataSet.data[tooltipLabelIndex];
                            //     return `${dataSet.label}: ${currencyFormatter(value)}`;
                            // }
                        }
                    }
                },
                aspectRatio: 1.0,
                scales: {
                    y: {
                        beginAtZero: true
                    }
                }
            }

            // tooltips: tooltipOptions,
            // scales: {
            //     y: [{
            //         ticks: {
            //             callback: (value: number, index, values) => {
            //                 return currencyFormatter(value);
            //             },
            //             beginAtZero: true
            //         },
            //     }]
            // }

            this.chart = new Chart(
                ctx,
                {
                    type: 'bar',
                    data: data,
                    options: chartOptions
                });
        }
    }
}


class NetPayablesChart extends BaseChart {


    renderChart() {

        if (this.chartData) {
            // @ts-ignore
            let netPayablesData = this.chartData.results['net_payable_data']
            let chartLabels = Object.keys(netPayablesData);
            let netPayablesDataSet = chartLabels.map(k => {
                // @ts-ignore
                return netPayablesData[k]
            });
            let chartLabelsFormatted = chartLabels.map(k => {
                // @ts-ignore
                return k.replace("_", " ").toUpperCase()
            });
            let data = {
                labels: chartLabelsFormatted,
                datasets: [
                    {
                        // label: 'Income',
                        borderColor: 'rgb(195,195,195)',
                        borderWidth: 0.75,
                        backgroundColor: [
                            'rgba(102, 24, 0, 1)',
                            'rgba(255, 95, 46, 1)',
                            'rgba(252, 190, 50, 1)',
                            'rgba(0,210,1,1)',
                            'rgba(225, 238, 246, 1)',
                        ],
                        data: netPayablesDataSet
                    }
                ]
            }


            // @ts-ignore
            const ctx = document.getElementById(this.selector) as ChartItem

            let chartOptions: ChartOptions = {

                plugins: {
                    title: {
                        display: true,
                        position: "top",
                        text: "Net Payables 0-90+ Days",
                        font: {
                            size: 20
                        }
                    },
                    tooltip: {
                        callbacks: {
                            // label(tooltipItem: TooltipItem<any>): string | string[] | void {
                            //     let dataSet = tooltipItem.dataset[tooltipItem.datasetIndex]
                            //     let tooltipLabelIndex = tooltipItem.dataIndex;
                            //     let value = dataSet.data[tooltipLabelIndex];
                            //     return `${dataSet.label}: ${currencyFormatter(value)}`;
                            // }
                        }
                    }
                },
                aspectRatio: 1.0,
                scales: {
                    y: {
                        beginAtZero: true
                    }
                }
            }

            this.chart = new Chart(ctx, {
                type: 'doughnut',
                data: data,
                options: chartOptions
            });
        }

    }

}


class NetReceivablesChart extends BaseChart {


    renderChart() {

        if (this.chartData) {
            // @ts-ignore
            let netPayablesData = this.chartData.results['net_receivable_data']
            let chartLabels = Object.keys(netPayablesData);
            let netPayablesDataSet = chartLabels.map(k => {
                // @ts-ignore
                return netPayablesData[k]
            });
            let chartLabelsFormatted = chartLabels.map(k => {
                // @ts-ignore
                return k.replace("_", " ").toUpperCase()
            });
            let data = {
                labels: chartLabelsFormatted,
                datasets: [
                    {
                        // label: 'Income',
                        borderColor: 'rgb(195,195,195)',
                        borderWidth: 0.75,
                        backgroundColor: [
                            'rgba(102, 24, 0, 1)',
                            'rgba(255, 95, 46, 1)',
                            'rgba(252, 190, 50, 1)',
                            'rgba(0,210,1,1)',
                            'rgba(225, 238, 246, 1)',
                        ],
                        data: netPayablesDataSet
                    }
                ]
            }


            // @ts-ignore
            // var ctx = document.getElementById(this.selector).getContext('2d');
            // let tooltipOptions: TooltipOptions = {
            //     callbacks: {
            //         label(
            //             tooltipItem: Chart.ChartTooltipItem,
            //             data: Chart.ChartData): string | string[] {
            //
            //             // @ts-ignore
            //             let dataSet = data.datasets[tooltipItem.datasetIndex];
            //             let tooltipLabelIndex = tooltipItem.index;
            //             let value = dataSet.data[tooltipLabelIndex];
            //
            //             return currencyFormatter(value);
            //
            //         }
            //     }
            // }
            //
            // let chartOptions: ChartOptions = {
            //     title: {
            //         display: true,
            //         position: "top",
            //         text: "Net Receivables 0-90+ Days",
            //         fontSize: 20
            //     },
            //     aspectRatio: 1.0,
            //     tooltips: tooltipOptions,
            //     legend: {
            //         position: "right"
            //     },
            // }

            const ctx = document.getElementById(this.selector) as ChartItem

            let chartOptions: ChartOptions = {

                plugins: {
                    title: {
                        display: true,
                        position: "top",
                        text: "Net Receivables 0-90+ Days",
                        font: {
                            size: 20
                        }
                    },
                    tooltip: {
                        callbacks: {
                            // label(tooltipItem: TooltipItem<any>): string | string[] | void {
                            //     let dataSet = tooltipItem.dataset[tooltipItem.datasetIndex]
                            //     let tooltipLabelIndex = tooltipItem.dataIndex;
                            //     let value = dataSet.data[tooltipLabelIndex];
                            //     return `${dataSet.label}: ${currencyFormatter(value)}`;
                            // }
                        }
                    }
                },
                aspectRatio: 1.0,
                scales: {
                    y: {
                        beginAtZero: true
                    }
                }
            }
            this.chart = new Chart(ctx, {
                type: 'doughnut',
                data: data,
                options: chartOptions
            });
        }

    }

}


export {
    PnLChart,
    NetPayablesChart,
    NetReceivablesChart
};

