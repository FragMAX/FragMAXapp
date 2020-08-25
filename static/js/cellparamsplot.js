let cellparamsPlotLoaded = false;

this.createcellparamsPlot = () => {
    if (cellparamsPlotLoaded) {
        return;
    }

    // set the dimensions and margins of the graph
    const margin = {
        top: 12,
        right: 0,
        bottom: 0,
        left: 30
    };

    const width = 660 - margin.left - margin.right;
    const height = 190;

    let paramsPlot;

    // set scale (linear=numeric) and range of paramsPlot axis
    const xScale = d3.scaleLinear().range([10, width - 10]);
    const yScale = d3.scaleLinear().range([height, 0]);

    //Read the data
    d3.json("/results/cellparams").then(data => {

        /* prepare the data for the chart */

        const datasetNames = Object.values(data.dataset);
        document.datasetsTotal = datasetNames.length;

        const keyscellParams = Object.keys(data).filter(key => key !== "dataset")
        const chartData = keyscellParams.map(key => {
            return datasetNames.map((d, idx) => {
                return {
                    dataset: idx,
                    cellParameter: data[key][idx]
                }
            })
        });

        /* calculate max&min values of y axis */
        const maxMeans = [];
        const minMeans = [];
        keyscellParams.forEach(key => {
            maxMeans.push(Math.max(...Object.values(data[key])));
            minMeans.push(Math.min(...Object.values(data[key])));
        });

        const yMax = Math.max(...maxMeans) + 10;
        const yMin = Math.min(...minMeans) - 10 > 0 ? Math.min(...minMeans) - 10 : 0;

        const xMin = -2;
        const xMax = datasetNames.length - 1;

        /**** Build the chart ****/

        /* colors for dots and error lines */
        const maxIVOrange = "#fea901";
        const maxIVGreen = "#82be00";
        const cyan = "#0fc1c1";
        const violet = "#c001c0";
        const red = "#ff0a0a"
        const blue = "#0d0dff";
        const colors = [blue, maxIVOrange, maxIVGreen, red, violet, cyan];

        paramsPlot = d3.select('#cellparams_plot')
            .append('svg')
            .attr("preserveAspectRatio", "xMinYMin meet")
            .attr("viewBox", "0 0 660 235")
            .append("g")
            .attr("transform",
                "translate(" + margin.left + "," + margin.top + ")");

        // set domain of axis scale
        xScale.domain([xMin, xMax]);
        yScale.domain([yMin, yMax]);

        // axis orientation and ticks (hided for axis-x)
        const xAxis = d3.axisBottom(xScale).tickFormat("");
        const yAxis = d3.axisLeft(yScale);

        const tooltip = d3.select('body').append('div').attr('class', 'tooltip');

        const legend = d3.select('#cellparams_legend').append('svg')
            .attr("viewBox", "0 0 38 65")
            .attr("preserveAspectRatio", "xMinYMin meet")
            .style('position', 'absolute')
            .style('right', '16px')
            .style('top', '46px')
            .style('width', '76px')
            .style('height', '90px')

        // Add legend dots
        legend.selectAll("legend_dots")
            .data(keyscellParams)
            .enter()
            .append("circle")
            .attr("cx", 5)
            .attr("cy", (d, i) => 5 + i * 10) // 35 is where the first dot appears. 10 is the distance between dots
            .attr("r", 2.5)
            .style("fill", (d, i) => colors[i])

        // Add legend labels
        legend.selectAll("legend_labels")
            .data(keyscellParams)
            .enter()
            .append("text")
            .attr("x", 10)
            .attr("y", (d, i) => 5 + i * 10)
            .text(d => d)
            .style("font-size", "8px").attr("alignment-baseline", "middle")

        const brush = d3.brush()
            .extent([
                [0, 0],
                [width, height]
            ])
            .on("end", brushended);

        let idleTimeout;
        const idleDelay = 350;

        paramsPlot.append('defs')
            .append('clipPath')
            .attr('id', 'clipCellParams')
            .append('rect')
            .attr('x', 10)
            .attr('y', 0)
            .attr('width', width - 10)
            .attr('height', height);

        // add brushing area (selection)
        paramsPlot.append("g")
            .attr("class", "params_brush")
            .call(brush);

        const sizeZoomedDot = 4;
        const sizeDefDot = 3;

        paramsPlot.selectAll(".cellParamseries")
            .data(chartData)
            .enter().append("g")
            .attr("class", "cellParamseries")
            .style("fill", (d, i) => colors[i])
            .selectAll(".cellparam_dot")
            .data(d => d)
            .enter().append("circle")
            .attr('clip-path', 'url(#clipCellParams)')
            .attr("class", "cellparam_dot")
            .attr("r", sizeDefDot)
            .attr("cx", d => xScale(d.dataset))
            .attr("cy", d => yScale(d.cellParameter))
            .attr("fill-opacity", .7)
            .attr("stroke-opacity", .7)
            .on('mouseover', function(d) {
                d3.select(this).attr("r", sizeZoomedDot);
                tooltip.transition()
                    .duration(0)
                    .style('opacity', 1)
                    .text(datasetNames[d.dataset] + '; a: ' + data.a[d.dataset] +
                        '; b: ' + data.b[d.dataset] + '; c: ' + data.c[d.dataset] +
                        '; \u03B1: ' + data.alpha[d.dataset] + '; \u03B2: ' + data.beta[d.dataset] +
                        '; \u03B3: ' + data.alpha[d.dataset])
                    .style('left', `${d3.event.pageX + 2}px`)
                    .style('top', `${d3.event.pageY - 18}px`);
            })
            .on('mouseout', function() {
                d3.select(this).attr("r", sizeDefDot);
                tooltip.transition()
                    .duration(0)
                    .style('opacity', 0);
            });

        // draw x axis
        paramsPlot.append("g")
            .attr("class", "axis axis--x")
            .attr("transform", "translate(0," + (height) + ")")
            .call(xAxis);

        // add x axis title
        paramsPlot.append("text")
            .attr("transform",
                "translate(" + (width / 2) + " ," +
                (height + margin.top + 15) + ")")
            .style("text-anchor", "middle")
            .style("font-size", "8px")
            .text("Dataset");

        // draw y axis
        paramsPlot.append("g")
            .attr("class", "axis axis--y")
            .attr("transform", "translate(10,0)")
            .call(yAxis);

        // add y axis title
        paramsPlot.append("text")
            .attr("transform", "rotate(-90)")
            .attr("y", 0 - margin.left)
            .attr("x", 0 - (height / 2))
            .attr("dy", "1em")
            .style("text-anchor", "middle")
            .style("font-size", "8px")
            .text("Cell Parameters");

        cellparamsPlotLoaded = true;

        // called when selected an area or zoom out
        function brushended() {
            const selectedArea = d3.event.selection;

            if (!selectedArea) {
                if (!idleTimeout) return idleTimeout = setTimeout(idled, idleDelay);
                // re-set default axis when zooming out
                xScale.domain([xMin, xMax]);
                yScale.domain([yMin, yMax]);
            } else { // if selection, rescale axis
                xScale.domain([selectedArea[0][0], selectedArea[1][0]].map(xScale.invert, xScale));
                yScale.domain([selectedArea[1][1], selectedArea[0][1]].map(yScale.invert, yScale));
                // remove gray area after selection
                paramsPlot.select(".params_brush").call(brush.move, null);
            }

            zoom();
        }

        function idled() {
            idleTimeout = null;
        }

        function zoom() {
            const selectedDatasets = new Set();
            const t = paramsPlot.transition().duration(0);
            paramsPlot.select(".axis--x").transition(t).call(xAxis);
            paramsPlot.select(".axis--y").transition(t).call(yAxis);
            paramsPlot.selectAll(".cellparam_dot").transition(t)
                .attr("cy", d => yScale(d.cellParameter))
                .attr("cx", d => {
                    const circleX = d.dataset;
                    const circleY = d.cellParameter;

                    // store selected datasets in a Set to filter the table
                    if (circleX >= xScale.domain()[0] &&
                        circleX <= xScale.domain()[1] &&
                        circleY <= yScale.domain()[1] &&
                        circleY >= yScale.domain()[0]) {
                        selectedDatasets.add(datasetNames[circleX]);
                    }
                    return xScale(circleX)
                });

            const threshold = document.getElementById('tshold_params').value;

            paramsPlot.selectAll('#params_threshold_line').transition(t)
                .attr('x1', 10)
                .attr('y1', yScale(threshold))
                .attr('x2', width)
                .attr('y2', yScale(threshold));

            // dispatch event with selection data
            const evt = new CustomEvent('dotsSelection', {
                bubbles: true,
                detail: {
                    data: [...selectedDatasets],
                    total: datasetNames.length
                }
            });
            document.getElementById('cellparams_plot').dispatchEvent(evt);

        }

    }).catch(err => console.log(err)); // end loading data and building paramsPlot

    document.createCellParamsThresholdLine = threshold => {
        // remove previous threshold line
        paramsPlot.selectAll('#params_threshold_line').remove();
        // threshold line color gray
        const maxIVGray = "#6e6e6e";
        // make new threshold line
        paramsPlot.append('line')
            .attr('id', 'params_threshold_line')
            .style('stroke', maxIVGray)
            .style('stroke-width', '1.5px')
            .attr('x1', xScale(xScale.domain()[0]))
            .attr('y1', yScale(threshold))
            .attr('x2', width)
            .attr('y2', yScale(threshold));
    }
}