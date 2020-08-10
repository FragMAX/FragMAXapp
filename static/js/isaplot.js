!(d3 => {

    // set the dimensions and margins of the graph
    const margin = {
        top: 4,
        right: 0,
        bottom: 0,
        left: 30
    };

    const width = 660 - margin.left - margin.right;
    const height = 190;

    // create div element for the tooltip
    const tooltip = d3.select('body').append('div')
        .attr('id', 'tooltip');

    const plot = d3.select('#isaplot')
        .append('svg')
        .attr("preserveAspectRatio", "xMinYMin meet")
        .attr("viewBox", "0 0 660 220")
        .append("g")
        .attr("transform",
            "translate(" + margin.left + "," + margin.top + ")");

    // colors
    const maxIVGreen = "#82be00";
    const maxIVOrange_85 = "#feb627";

    // set scale (linear=numeric) and range for axis x and y
    const xScale = d3.scaleLinear().range([10, width - 10]);
    const yScale = d3.scaleLinear().range([height, 0]);

    //Read the data
    d3.json("/results/isa").then((data, error) => {

        if (error) throw error;

        const datasetNames = Object.values(data.dataset);
        document.datasetsTotal = datasetNames.length;
        // create array of datasetnames indexes to be used as numeric scale for x axis
        const datasetNums = [];
        Object.keys(data.dataset).forEach(key => datasetNums.push(+key));

        /* calculate max value of y axis */
        const meanValues = Object.values(data.mean);
        const maxMean = Math.max(...meanValues);
        const minMean = Math.min(...meanValues);

        const yMax = Math.round(maxMean) + 3;
        const yMin = Math.round(minMean) - 3 >= 1 ? Math.round(minMean) - 3 : 0;

        const xMin = -2;
        const xMax = datasetNums.length - 1;

        // set domain of axis scale
        xScale.domain([xMin, xMax]);
        yScale.domain([yMin, yMax]);

        // axis orientation and ticks (hided for axis-x)
        const xAxis = d3.axisBottom(xScale).tickFormat("");
        const yAxis = d3.axisLeft(yScale);

        // create area for selection event 
        const brush = d3.brush()
            .extent([
                [0, 0],
                [width, height]
            ])
            .on("end", brushended);

        let idleTimeout;
        const idleDelay = 350;

        // create array to be used as data for d3 plot
        const dataArray = datasetNums.map((d, idx) => {
            return {
                dataset: d,
                mean: data.mean[idx],
                std: data.std[idx]
            }
        });

        // create clipping area to prevent zoomed dots from displaying outside plot area
        plot.append('defs')
            .append('clipPath')
            .attr('id', 'clip')
            .append('rect')
            .attr('x', 10)
            .attr('y', 0)
            .attr('width', width - 10)
            .attr('height', height);

        // add brushing (selection area)
        plot.append("g")
            .attr("class", "brush")
            .call(brush);


        const zoomedDotSize = 4;
        const defDotSize = 3;


        // add dots 
        plot.selectAll("circle")
            .data(dataArray)
            .enter()
            .append("circle")
            .attr('clip-path', 'url(#clip)')
            .attr("cx", d => xScale(d.dataset))
            .attr("cy", d => yScale(d.mean))
            .attr("r", defDotSize)
            .style("fill", maxIVGreen)
            .on('mouseover', function(d) {
                d3.select(this).attr("r", zoomedDotSize);
                // xAxis.tickFormat(d => datasetNames[d]).tickValues([d.dataset]);
                // plot.selectAll('.axis--x').call(xAxis);
                tooltip.transition()
                    .duration(0)
                    .style('opacity', 1)
                    .text(datasetNames[d.dataset] + '; isa: ' + d.mean)
                    .style('left', `${d3.event.pageX + 2}px`)
                    .style('top', `${d3.event.pageY - 18}px`);
            })
            .on('mouseout', function(d) {
                d3.select(this).attr("r", defDotSize);
                tooltip.transition()
                    .duration(0)
                    .style('opacity', 0);
            });

        // add standard error lines
        const lines = plot.selectAll('line.error').data(dataArray);
        lines.enter()
            .append('line')
            .style('stroke', maxIVGreen)
            .attr('class', 'error')
            .attr('clip-path', 'url(#clip)')
            .merge(lines)
            .attr('x1', d => xScale(d.dataset))
            .attr('x2', d => xScale(d.dataset))
            .attr('y1', d => yScale(d.mean + d.std))
            .attr('y2', d => yScale(d.mean - d.std));

        // draw x axis
        plot.append("g")
            .attr("class", "axis axis--x")
            .attr("transform", "translate(0," + (height) + ")")
            .call(xAxis);

        // x axis title
        plot.append("text")
            .attr("id", "xLabel")
            .attr("transform",
                "translate(" + (width / 2) + " ," +
                (height + margin.top + 15) + ")")
            .style("text-anchor", "middle")
            .style("font-size", "8px")
            .text("Dataset");

        // draw y axis
        plot.append("g")
            .attr("class", "axis axis--y")
            .attr("transform", "translate(10,0)")
            .call(yAxis);

        // y axis title
        plot.append("text")
            .attr("transform", "rotate(-90)")
            .attr("y", 0 - margin.left + 5)
            .attr("x", 0 - (height / 2))
            .attr("dy", "1em")
            .style("text-anchor", "middle")
            .style("font-size", "8px")
            .text("ISa");

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
                plot.select(".brush").call(brush.move, null);
            }
            zoom();
        }

        function idled() {
            idleTimeout = null;
        }

        function zoom() {

            const selectedDatasets = [];
            const t = plot.transition().duration(0);
            plot.select(".axis--x").transition(t).call(xAxis);
            plot.select(".axis--y").transition(t).call(yAxis);
            plot.selectAll("circle").transition(t)
                .attr("cx", function(d) {
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

            plot.selectAll("line.error").transition(t)
                .attr('x1', d => xScale(d.dataset))
                .attr('x2', d => xScale(d.dataset))
                .attr('y1', d => getStdErrPos(d, 'y1'))
                .attr('y2', d => getStdErrPos(d, 'y2'));

            const threshold = document.getElementById('tshold_isa').value;
            plot.selectAll('#threshold-line').transition(t)
                .attr('x1', 10)
                .attr('y1', yScale(threshold))
                .attr('x2', width)
                .attr('y2', yScale(threshold));

            const isaplot = document.getElementById('isaplot');
            const evt = new CustomEvent('dotsSelection', {
                bubbles: true,
                detail: selectedDatasets
            });
            isaplot.dispatchEvent(evt);

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

    });

    this.createIsaThresholdLine = (threshold) => {
        // remove previous threshold line
        plot.selectAll('#threshold-line').remove();
        // make new threshold line
        plot.append('line')
            .attr('id', 'threshold-line')
            .style('stroke', maxIVOrange_85)
            .style('stroke-width', '2.5px')
            .attr('x1', xScale(xScale.domain()[0]))
            .attr('y1', yScale(threshold))
            .attr('x2', width)
            .attr('y2', yScale(threshold));
    }

})(d3);