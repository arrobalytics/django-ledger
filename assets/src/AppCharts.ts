import Chart, {
    ChartOptions,
    ChartScales,
    ChartTitleOptions,
    ChartTooltipCallback,
    ChartTooltipOptions,
    TickOptions
} from "chart.js";
import Axios, {AxiosInstance, AxiosResponse} from "axios";


interface EntityPnLDataResponse {
    entity_slug: string,
    entity_name: string,
    pnl_data: object
}

interface DjangoLedgerJSONDataResponse {
    results: EntityPnLDataResponse
}


class PnLChart {

    selector: string;
    endPoint: string;
    chart: Chart | undefined;
    chartData: DjangoLedgerJSONDataResponse | undefined;
    http: AxiosInstance | undefined;
    entitySlug: string;
    consoleLogData: boolean = false;
    lazyGetData: boolean = false;


    constructor(selector: string, entitySlug: string) {
        this.entitySlug = entitySlug;
        this.endPoint = this.getEndPoint();
        this.selector = selector;
        this.getHttpClient()
    }

    getEndPoint() {
        return `entity/${this.entitySlug}/data/pnl/`
    }

    getHttpClient() {
        this.http = Axios.create({
            baseURL: 'http://127.0.0.1:8000/'
        })
        if (!this.lazyGetData) {
            this.getChartData()
        }
    }

    getChartData() {
        this.http?.get(
            this.endPoint
        ).then((r: AxiosResponse<DjangoLedgerJSONDataResponse>) => {
            this.chartData = r.data;
            if (this.consoleLogData) {
                console.log(r);
            }
            this.renderChart()
        })
    }


    renderChart() {

        if (this.chartData) {
            let entityName = this.chartData.results.entity_name
            let pnlData = this.chartData.results.pnl_data
            let chartLabels = Object.keys(pnlData);
            let revenue = chartLabels.map(k => {
                // @ts-ignore
                return pnlData[k]['GROUP_INCOME']
            })
            let netIncome = chartLabels.map(k => {
                // @ts-ignore
                return pnlData[k]['GROUP_EARNINGS']
            })

            let data = {
                labels: chartLabels,
                datasets: [
                    {
                        label: 'Income',
                        backgroundColor: 'rgb(255,127,153)',
                        borderColor: 'rgb(255, 99, 132)',
                        data: revenue
                    },
                    {
                        label: 'Earnings',
                        backgroundColor: 'rgb(110,210,81)',
                        borderColor: 'rgb(115,255,99)',
                        data: netIncome
                    }]
            }

            // @ts-ignore
            var ctx = document.getElementById(this.selector).getContext('2d');
            let chartTitleOptions: ChartTitleOptions = {
                display: true,
                text: `${entityName} - Income & Earnings`,
                fontSize: 20
            }

            let chartOptions: ChartOptions = {
                title: chartTitleOptions
            }

            this.chart = new Chart(ctx, {
                type: 'bar',
                data: data,
                options: chartOptions
            });
        }

    }

}

interface EntityPnLDataResponse2 {
    entity_slug: string,
    net_payable_data: object
}

interface DjangoLedgerJSONDataResponse2 {
    results: EntityPnLDataResponse2
}


class NetPayablesChart {

    selector: string;
    endPoint: string;
    chart: Chart | undefined;
    chartData: DjangoLedgerJSONDataResponse2 | undefined;
    http: AxiosInstance | undefined;
    entitySlug: string;
    consoleLogData: boolean = false;
    lazyGetData: boolean = false;


    constructor(selector: string, entitySlug: string) {
        this.entitySlug = entitySlug;
        this.endPoint = this.getEndPoint();
        this.selector = selector;
        this.getHttpClient()
    }

    getEndPoint() {
        return `entity/${this.entitySlug}/data/net-payables/`
    }

    getHttpClient() {
        this.http = Axios.create({
            baseURL: 'http://127.0.0.1:8000/'
        })
        if (!this.lazyGetData) {
            this.getChartData()
        }
    }

    getChartData() {
        this.http?.get(
            this.endPoint
        ).then((r: AxiosResponse<DjangoLedgerJSONDataResponse2>) => {
            this.chartData = r.data;
            if (this.consoleLogData) {
                console.log(r);
            }
            this.renderChart()
        })
    }

    renderChart() {

        if (this.chartData) {
            // let entityName = this.chartData.results.entity_name
            let netPayablesData = this.chartData.results.net_payable_data
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
                            'rgba(225, 238, 246, 1)',
                            'rgba(252, 190, 50, 1)',
                            'rgba(0, 78, 102, 1)',
                            'rgba(255, 95, 46, 1)',
                            'rgba(102, 24, 0, 1)'],
                        data: netPayablesDataSet
                    }
                ]
            }


            // @ts-ignore
            var ctx = document.getElementById(this.selector).getContext('2d');
            let chartTitleOptions: ChartTitleOptions = {
                display: true,
                text: "Net Payables 0-90+ Days",
                fontSize: 20
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
                        return Intl.NumberFormat(
                            'en-US',
                            {style: 'currency', currency: 'USD', minimumFractionDigits: 0})
                            .format(value);
                    }
                }
            }

            let chartOptions: ChartOptions = {
                title: chartTitleOptions,
                tooltips: tooltipOptions
            }

            this.chart = new Chart(ctx, {
                type: 'doughnut',
                data: data,
                options: chartOptions
            });
        }

    }

}

export {PnLChart, NetPayablesChart};

