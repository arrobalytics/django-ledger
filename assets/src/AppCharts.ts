import Chart, {ChartOptions, ChartTooltipOptions} from "chart.js";
import Axios, {AxiosInstance, AxiosRequestConfig, AxiosResponse} from "axios";

function currencyFormatter(value: number): string {
    return Intl.NumberFormat(
        'en-US',
        {style: 'currency', currency: 'USD'})
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
    startDate: string | null
    endDate: string | null

    constructor(selector: string,
                entitySlug: string,
                startDate: string | null,
                endDate: string | null,
                chartData = undefined) {
        this.selector = selector
        this.startDate = startDate
        this.endDate = endDate

        if (!chartData) {
            this.startHttpClient()
        } else {
            this.chartData = chartData
        }

        this.entitySlug = entitySlug;
    }

    getEndPoint(): string | undefined {
        // @ts-ignore
        return document.getElementById(this.selector).dataset.endpoint
    }

    getChartData() {
        if (!this.chartData) {
            let axiosConfig: AxiosRequestConfig = {
                params: {
                    startDate: this.startDate ? this.startDate : null,
                    endDate: this.endDate ? this.endDate : null,
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
                        backgroundColor: 'rgb(110,210,81)',
                        borderColor: 'rgb(115,255,99)',
                        data: income
                    },
                    {
                        label: 'Expenses',
                        backgroundColor: 'rgb(255,127,153)',
                        borderColor: 'rgb(255, 99, 132)',
                        data: expenses
                    }]
            }

            let tooltipOptions: ChartTooltipOptions = {
                callbacks: {
                    label(
                        tooltipItem: Chart.ChartTooltipItem,
                        data: Chart.ChartData): string | string[] {

                        // @ts-ignore
                        let dataSet = data.datasets[tooltipItem.datasetIndex];
                        let tooltipLabelIndex = tooltipItem.index;
                        let value = dataSet.data[tooltipLabelIndex];

                        return `${dataSet.label}: ${currencyFormatter(value)}`;

                    }
                }
            }


            // @ts-ignore
            var ctx = document.getElementById(this.selector).getContext('2d');
            let chartOptions: ChartOptions = {
                title: {
                    display: true,
                    text: `${entityName} - Income & Expenses`,
                    fontSize: 20
                },
                aspectRatio: 1.0,
                tooltips: tooltipOptions,
                scales: {
                    yAxes: [{
                        ticks: {
                            callback: (value: number, index, values) => {
                                return currencyFormatter(value);
                            },
                            beginAtZero: true
                        },
                    }]
                }
            }

            this.chart = new Chart(ctx, {
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
            var ctx = document.getElementById(this.selector).getContext('2d');
            let tooltipOptions: ChartTooltipOptions = {
                callbacks: {
                    label(
                        tooltipItem: Chart.ChartTooltipItem,
                        data: Chart.ChartData): string | string[] {

                        // @ts-ignore
                        let dataSet = data.datasets[tooltipItem.datasetIndex];
                        let tooltipLabelIndex = tooltipItem.index;
                        let value = dataSet.data[tooltipLabelIndex];

                        return currencyFormatter(value);

                    }
                }
            }

            let chartOptions: ChartOptions = {
                title: {
                    display: true,
                    position: "top",
                    text: "Net Payables 0-90+ Days",
                    fontSize: 20
                },
                aspectRatio: 1,
                tooltips: tooltipOptions,
                legend: {
                    position: "right"
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
            var ctx = document.getElementById(this.selector).getContext('2d');
            let tooltipOptions: ChartTooltipOptions = {
                callbacks: {
                    label(
                        tooltipItem: Chart.ChartTooltipItem,
                        data: Chart.ChartData): string | string[] {

                        // @ts-ignore
                        let dataSet = data.datasets[tooltipItem.datasetIndex];
                        let tooltipLabelIndex = tooltipItem.index;
                        let value = dataSet.data[tooltipLabelIndex];

                        return currencyFormatter(value);

                    }
                }
            }

            let chartOptions: ChartOptions = {
                title: {
                    display: true,
                    position: "top",
                    text: "Net Receivables 0-90+ Days",
                    fontSize: 20
                },
                aspectRatio: 1.0,
                tooltips: tooltipOptions,
                legend: {
                    position: "right"
                },
            }

            this.chart = new Chart(ctx, {
                type: 'doughnut',
                data: data,
                options: chartOptions
            });
        }

    }

}

export {PnLChart, NetPayablesChart, NetReceivablesChart};

