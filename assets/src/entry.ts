import {DjetlerApp} from "./DjetlerApp";
import {NetPayablesChart, PnLChart} from "./AppCharts";


export function startDJLApp() {
    return new DjetlerApp();
}

export function renderPnLChart(selector: string, entitySlug: string) {
    return new PnLChart(selector, entitySlug);
}

export function renderNetPayablesChart(selector: string, entitySlug: string) {
    return new NetPayablesChart(selector, entitySlug);
}