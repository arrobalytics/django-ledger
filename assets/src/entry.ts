import {DjetlerApp} from "./DjetlerApp";
import {ProfitChart} from "./AppCharts";


export function startDJLApp() {
    return new DjetlerApp();
}

export function renderProfitChart(id: string) {
    return new ProfitChart(id);
}