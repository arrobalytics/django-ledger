import Chart, {ChartOptions, ChartTitleOptions} from "chart.js";
import Axios, {AxiosInstance, AxiosResponse} from "axios";


interface EntityDataDetailResponse {
    entity_slug: string,
    entity_name: string,
    entity_data: object
}

interface EntityDataResponse {
    results: EntityDataDetailResponse
}


class RevenueAndNetIncome {

    selector: string;
    endPoint: string;
    chart: Chart | undefined;
    chartData: EntityDataResponse | undefined;
    http: AxiosInstance | undefined;
    entitySlug: string;


    constructor(selector: string, entitySlug: string) {
        this.entitySlug = entitySlug;
        this.endPoint = `entity/${this.entitySlug}/data/`;
        this.selector = selector;
        this.getHttpClient()
        // this.renderChart()
    }

    getHttpClient() {
        this.http = Axios.create({
            baseURL: 'http://127.0.0.1:8000/'
        })
        this.getChartData()
    }

    getChartData() {
        this.http?.get(
            this.endPoint
        ).then((r: AxiosResponse<EntityDataResponse>) => {
            this.chartData = r.data;
            this.renderChart()
        })
    }


    renderChart() {

        if (this.chartData) {
            let entityName = this.chartData.results.entity_name
            let entityData = this.chartData.results.entity_data
            let chartLabels = Object.keys(entityData);
            let revenue = chartLabels.map(k => {
                // @ts-ignore
                return entityData[k]['GROUP_INCOME']
            })
            let netIncome = chartLabels.map(k => {
                // @ts-ignore
                return entityData[k]['GROUP_EARNINGS']
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

export {RevenueAndNetIncome};
