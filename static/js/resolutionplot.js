let resPlotLoaded = false;

this.createResolutionPlot = () => {
    if (resPlotLoaded) {
        return;
    }

    // set the dimensions and margins of the graph
    const margin = {
        top: 4,
        right: 0,
        bottom: 0,
        left: 30
    };

    const width = 660 - margin.left - margin.right;
    const height = 190;

    const resolutionPlot = d3.select('#resolutionplot')
            .append('svg')
            .attr("preserveAspectRatio", "xMinYMin meet")
            .attr("viewBox", "0 0 660 220")
            .append("g")
            .attr("transform",
                "translate(" + margin.left + "," + margin.top + ")");

    // set scale for axis x and y
    const xScale = d3.scaleLinear().range([10, width - 10]);
    const yScale = d3.scaleLinear().range([height, 0]);

    //Read the data
    d3.json("/results/resolution").then(data => {


        /* process results data */
        const datasetNames = Object.values(data.dataset);

        /* calculate max value of y axis */
        const meanValues = Object.values(data.mean);
        const maxMean = Math.max(...meanValues);
        const minMean = Math.min(...meanValues);

        const yMax = maxMean + 0.05;
        const yMin = minMean - 0.05 >= 0 ? minMean - 0.05 : 0;

        const xMin = -2;
        const xMax = datasetNames.length - 1;

        // prepare data to be used as data for the plot
        const dataArray = datasetNames.map((d, idx) => {
            return {
                dataset: idx,
                mean: data.mean[idx],
                std: data.std[idx]
            }
        });

        /* build the chart */

        // set domain of axis scales
        xScale.domain([xMin, xMax]);
        yScale.domain([yMin, yMax]);

        // axis orientation and ticks (hided for axis-x)
        const xAxis = d3.axisBottom(xScale).tickFormat("");
        const yAxis = d3.axisLeft(yScale);
        
        // create div element for the tooltip
        const tooltip = d3.select('body').append('div')
            .attr('class', 'tooltip');

        // create area for selection event
        const brush = d3.brush()
            .extent([
                [0, 0],
                [width, height]
            ])
            .on("end", brushended);

        let idleTimeout;
        const idleDelay = 350;

        // create clipping area to prevent zoomed dots from displaying outside plot area
        resolutionPlot.append('defs')
            .append('clipPath')
            .attr('id', 'resClip')
            .append('rect')
            .attr('x', 10)
            .attr('y', 0)
            .attr('width', width - 10)
            .attr('height', height);

        // add brushing (selection area)
        resolutionPlot.append("g")
            .attr("id", "res_brush")
            .call(brush);

        // dot size
        const zoomedDotSize = 4;
        const defDotSize = 3;
        // dot and error line color
        const maxIVGreen = "#82be00";

        // add dots
        resolutionPlot.selectAll(".res_dot")
            .data(dataArray)
            .enter()
            .append("circle")
            .attr("class", "res_dot")
            .attr('clip-path', 'url(#resClip)')
            .attr("cx", d => xScale(d.dataset))
            .attr("cy", d => yScale(d.mean))
            .attr("r", defDotSize)
            .style("fill", maxIVGreen)
            .on('mouseover', function(d) {
                d3.select(this).attr("r", zoomedDotSize);
                tooltip.transition()
                    .duration(0)
                    .style('opacity', 1)
                    .text(datasetNames[d.dataset] + '; resolution: ' + d.mean)
                    .style('left', `${d3.event.pageX + 2}px`)
                    .style('top', `${d3.event.pageY - 18}px`);
            })
            .on('mouseout', function() {
                d3.select(this).attr("r", defDotSize);
                tooltip.transition()
                    .duration(0)
                    .style('opacity', 0);
            });

        // add standard error lines
        const err_res_lines = resolutionPlot.selectAll('line.res_error').data(dataArray);
        err_res_lines.enter()
            .append('line')
            .style('stroke', maxIVGreen)
            .attr('class', 'res_error')
            .attr('clip-path', 'url(#resClip)')
            .merge(err_res_lines)
            .attr('x1', d => xScale(d.dataset))
            .attr('x2', d => xScale(d.dataset))
            .attr('y1', d => yScale(d.mean + d.std))
            .attr('y2', d => yScale(d.mean - d.std));

        // draw x axis
        resolutionPlot.append("g")
            .attr("class", "axis axis--x")
            .attr("transform", "translate(0," + (height) + ")")
            .call(xAxis);

        // x axis title
        resolutionPlot.append("text")
            .attr("id", "xLabel")
            .attr("transform",
                "translate(" + (width / 2) + " ," +
                (height + margin.top + 15) + ")")
            .style("text-anchor", "middle")
            .style("font-size", "8px")
            .text("Dataset");

        // draw y axis
        resolutionPlot.append("g")
            .attr("class", "axis axis--y")
            .attr("transform", "translate(10,0)")
            .call(yAxis);

        // y axis title
        resolutionPlot.append("text")
            .attr("transform", "rotate(-90)")
            .attr("y", 0 - margin.left)
            .attr("x", 0 - (height / 2))
            .attr("dy", "1em")
            .style("text-anchor", "middle")
            .style("font-size", "8px")
            .text("resolution");

        resPlotLoaded = true;

        // called when selected an area, or double click
        function brushended() {
            const selection = d3.event.selection;

            // if no selection: set x and y axis to default values
            if (!selection) {
                if (!idleTimeout) return idleTimeout = setTimeout(idled, idleDelay);
                // re-set default axis when zooming out
                xScale.domain([xMin, xMax]);
                yScale.domain([yMin, yMax]);
            } else { // if selection, rescale axis
                xScale.domain([selection[0][0], selection[1][0]].map(xScale.invert, xScale));
                yScale.domain([selection[1][1], selection[0][1]].map(yScale.invert, yScale));
                // remove gray area after selection
                resolutionPlot.select("#res_brush").call(brush.move, null);
            }
            zoom();
        }

        function idled() {
            idleTimeout = null;
        }

        function zoom() {
            const selectedDatasets = [];
            const t = resolutionPlot.transition().duration(0);
            resolutionPlot.select(".axis--x").transition(t).call(xAxis);
            resolutionPlot.select(".axis--y").transition(t).call(yAxis);
            resolutionPlot.selectAll(".res_dot").transition(t)
                .attr("cx", d => {
                    const circleDatasetIdx = d.dataset;
                    const circleMean = d.mean;
                    // store selected dots in a variable to be used to display table of selected data
                    if (circleDatasetIdx >= xScale.domain()[0] &&
                        circleDatasetIdx <= xScale.domain()[1] &&
                        circleMean <= yScale.domain()[1] &&
                        circleMean >= yScale.domain()[0]) {
                        selectedDatasets.push(datasetNames[circleDatasetIdx]);
                    }
                    return xScale(circleDatasetIdx);
                })
                .attr("cy", d => yScale(d.mean));

            resolutionPlot.selectAll("line.res_error").transition(t)
                .attr('x1', d => xScale(d.dataset))
                .attr('x2', d => xScale(d.dataset))
                .attr('y1', d => getStdErrPos(d, 'y1'))
                .attr('y2', d => getStdErrPos(d, 'y2'));

            const threshold = document.getElementById('tshold_res').value;
            resolutionPlot.selectAll('#res_threshold_line').transition(t)
                .attr('x1', 10)
                .attr('y1', yScale(threshold))
                .attr('x2', width)
                .attr('y2', yScale(threshold));

            // pass selection data to event and dispatch it
            const evt = new CustomEvent('dotsSelection', {
                bubbles: true,
                detail: {
                    data: selectedDatasets,
                    total: datasetNames.length
                }
            });
            document.getElementById('resolutionplot').dispatchEvent(evt);
        } // end zoom

        // hide error lines of dots outside selection range
        function getStdErrPos(data_row, yVal) {
            switch (yVal) {
                case "y1":
                    return data_row.mean > yScale.domain()[0] && data_row.mean < yScale.domain()[1] ?
                        yScale(data_row.mean + data_row.std) : yScale(0);
                case "y2":
                    return data_row.mean > yScale.domain()[0] && data_row.mean < yScale.domain()[1] ?
                        yScale(data_row.mean - data_row.std) : yScale(0);
                default:
                    return yScale(0);
            }
        }

    }).catch(err => console.log(err)); // end loading data and building plot

    document.createResolutionThresholdLine = (threshold) => {
        // remove previous threshold line
        resolutionPlot.selectAll('#res_threshold_line').remove();
        // threshold line color: orange 85%
        const maxIVOrange_85 = "#feb627";
        // make new threshold line
        resolutionPlot.append('line')
            .attr('id', 'res_threshold_line')
            .style('stroke', maxIVOrange_85)
            .style('stroke-width', '1.5px')
            .attr('x1', xScale(xScale.domain()[0]))
            .attr('y1', yScale(threshold))
            .attr('x2', width)
            .attr('y2', yScale(threshold));
    }
}
