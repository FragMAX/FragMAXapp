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

  const tooltip = d3.select('body').append('div').attr('class', 'tooltip');
  const legend = d3.select('#rfactor_legend').append('svg')
    .style('position', 'absolute')
    .style('right', '20px')
    .style('top', '32px')
    .style('width', '70px')
    .style('height', '36px')

  legend.append("circle").attr("cx", 35).attr("cy", 20).attr("r", 2.5).style("fill", "green")
  legend.append("circle").attr("cx", 35).attr("cy", 30).attr("r", 2.5).style("fill", "orange")
  legend.append("text").attr("x", 40).attr("y", 20).text("Rfree").style("font-size", "10px").attr("alignment-baseline", "middle")
  legend.append("text").attr("x", 40).attr("y", 30).text("Rwork").style("font-size", "10px").attr("alignment-baseline", "middle")

  const plot = d3.select('#rfactors_plot')
    .append('svg')
    .attr("preserveAspectRatio", "xMinYMin meet")
    .attr("viewBox", "0 0 660 220")
    .append("g")
    .attr("transform",
      "translate(" + margin.left + "," + margin.top + ")");

  // set scale (linear=numeric) and range of plot axis
  const xScale = d3.scaleLinear().range([10, width - 10]);
  const yScale = d3.scaleLinear().range([height, 0]);

  /* colors */
  const maxIVOrange = "#fea901";
  const maxIVGreen = "#82be00";
  const maxIVGray = "#6e6e6e";

  //Read the data
  d3.json("/results/rfactor").then((data, error) => {

    if(error) throw error;

    const datasetNames = Object.values(data.dataset);
    document.datasetsTotal = datasetNames.length;
    // create array of datasetnames indexes so we can use it as a numeric scale for x axis
    const datasetIdxs = [];
    Object.keys(data.dataset).forEach(key => datasetIdxs.push(+key));

    const keysRfactors = ["rwork", "rfree"];
    const valuesRfactors = keysRfactors.map(key => {
      return datasetIdxs.map(datasetIdx => {
        return {
          dataset: datasetIdx,
          rfactor: data[key][datasetIdx]
        }
      })
    });

    const rwork_values = valuesRfactors[0];
    rwork_values.forEach((obj, idx) => obj.std = data.std_rw[idx])
    const rfree_values = valuesRfactors[1];
    rfree_values.forEach((obj, idx) => obj.std = data.std_rf[idx])

    // create array of data to be used for the plot
    const dataArray = [];
    dataArray.push(rwork_values);
    dataArray.push(rfree_values);

    /* calculate max&min values of y axis */
    const rwValues = Object.values(data.rwork);
    const rfValues = Object.values(data.rfree);
    const max_rw = Math.max(...rwValues);
    const max_rf = Math.max(...rfValues);
    const min_rw = Math.min(...rwValues);
    const min_rf = Math.min(...rfValues);

    const yMax = Math.max(max_rw, max_rf) + 0.05;
    const rValuesMin = Math.min(min_rw, min_rf) - 0.05;
    const yMin = rValuesMin > 0 ? rValuesMin : 0;

    const xMin = -2;
    const xMax = datasetIdxs.length - 1;

    // set domain of axis scale
    xScale.domain([xMin, xMax]);
    yScale.domain([yMin, yMax]);

    // axis orientation and ticks (hided for axis-x)
    const xAxis = d3.axisBottom(xScale).tickFormat("");
    const yAxis = d3.axisLeft(yScale);

    const brush = d3.brush()
      .extent([
        [0, 0],
        [width, height]
      ])
      .on("end", brushended);

    let idleTimeout;
    const idleDelay = 350;

    const colors = [maxIVOrange, maxIVGreen];

    plot.append('defs')
        .append('clipPath')
        .attr('id', 'clipR')
        .append('rect')
        .attr('x', 10)
        .attr('y', 0)
        .attr('width', width-10)
        .attr('height', height);

    // add brushing area (selection)
    plot.append("g")
      .attr("class", "brush")
      .call(brush);

    const sizeZoomedDot = 4;
    const sizeDefDot = 3;

    plot.selectAll(".rFactorSeries")
      .data(dataArray)
      .enter().append("g")
      .attr("class", "rFactorSeries")
      .style("fill", (d, i) => colors[i])
      .selectAll(".rfact_dot")
      .data(d => d)
      .enter().append("circle")
      .attr('clip-path', 'url(#clipR)')
      .attr("class", "rfact_dot")
      .attr("r", sizeDefDot)
      .attr("cx", d => xScale(d.dataset))
      .attr("cy", d => yScale(d.rfactor))
      .attr("fill-opacity", 0.6)
      .on('mouseover', function(d) {
        d3.select(this).attr("r", sizeZoomedDot);
        tooltip.transition()
          .duration(0)
          .style('opacity', 1)
          .text(datasetNames[d.dataset] + '; R: ' + d.rfactor)
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
    plot.append("g")
      .attr("class", "axis axis--x")
      .attr("transform", "translate(0," + (height) + ")")
      .call(xAxis);

    // add x axis title
    plot.append("text")
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

    // add y axis title
    plot.append("text")
      .attr("transform", "rotate(-90)")
      .attr("y", 0 - margin.left)
      .attr("x", 0 - (height / 2))
      .attr("dy", "1em")
      .style("text-anchor", "middle")
      .style("font-size", "8px")
      .text("r_factors");

    // add error lines for standard error data series (std_rwork and std_rfree)
    plot.selectAll(".stdErrSeries")
      .data(dataArray)
      .enter().append("g")
      .attr("class", "stdErrSeries")
      .style("stroke", (d, i) => colors[i])
      .selectAll("line.error")
      .data(d => d)
      .enter().append("line")
      .attr("class", "error")
      .attr('clip-path', 'url(#clipR)')
      .attr('x1', d => xScale(d.dataset))
      .attr('x2', d => xScale(d.dataset))
      .attr('y1', d => yScale(d.rfactor + d.std))
      .attr('y2', d => yScale(d.rfactor - d.std));

    // called when selected an area, or double click
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
        plot.select(".brush").call(brush.move, null);
      }

      zoom();
    }

    function idled() {
      idleTimeout = null;
    }

    function zoom() {
      const t = plot.transition().duration(0);
      plot.select(".axis--x").transition(t).call(xAxis);
      plot.select(".axis--y").transition(t).call(yAxis);
      plot.selectAll(".rfact_dot").transition(t)
          .attr("cy", d => yScale(d.rfactor))
          .attr("cx", d => xScale(d.dataset));

      plot.selectAll("line.error").transition(t)
        .attr('x1', d => xScale(d.dataset))
        .attr('x2', d => xScale(d.dataset))
        .attr('y1', d => yScale(d.rfactor + d.std))
        .attr('y2', d => yScale(d.rfactor - d.std));

      const threshold = document.getElementById('tshold_rfactor').value;
      plot.selectAll('#rf_threshold_line').transition(t)
        .attr('x1', 10)
        .attr('y1', yScale(threshold))
        .attr('x2', width)
        .attr('y2', yScale(threshold));

    }

  });

  document.createRfactorThresholdLine = threshold => {
    // remove previous threshold line
    plot.selectAll('#rf_threshold_line').remove();
    // make new threshold line
    plot.append('line')
      .attr('id', 'rf_threshold_line')
      .style('stroke', maxIVGray)
      .style('stroke-width', '2.5px')
      .attr('x1', xScale(xScale.domain()[0]))
      .attr('y1', yScale(threshold))
      .attr('x2', width)
      .attr('y2', yScale(threshold));
  }

})(d3);
