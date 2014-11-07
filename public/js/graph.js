/*
	 Object structure derived from comment 54 in: 
	 http://stackoverflow.com/questions/1595611/how-to-properly-create-a-custom-object-in-javascript
*/
var Graphkit = function (){

	var constructor = function (chartid, height, seriesData) {
		
		// PRIVATE VARS
		var _chartid = chartid;
		var _height =  height;
		var _seriesData = seriesData;
		var _palette = new Rickshaw.Color.Palette( { scheme: 'colorwheel' } );
		var _graph;
        var _graphscontainer = "charts"; // should be an elemnt id
		var _preview;

		// PUBLIC METHODS: this.publicMethod = function() {};
		this.build = function (data){
		    // Colorise the lines
		    for (i = 0; i < data.length; i++) {
		        console.log( data[i]['color'] )
                data[i]['color'] = _palette.color(); 
		    }
		    // Then build the graph
            buildall(data);
            bindresizeevent();
        }
        
        this.testdata = function (){
			var datalen = 10
			_seriesData = [ [], [], [], [], [], [], [], [], [] ];
			var random = new Rickshaw.Fixtures.RandomData(datalen); 
	 		for (var i = 0; i < datalen; i++) {
     			random.addData(_seriesData);
			}
            //js = JSON.stringify(_seriesData)
			//console.log(js);
            var thedata = [
							{color: _palette.color(),data: _seriesData[0],name: 'CO2'}, 
							{color: _palette.color(),data: _seriesData[1],name: 'NO2'}, 
							{color: _palette.color(),data: _seriesData[2],name: 'PM'}, 
							{color: _palette.color(),data: _seriesData[3],name: 'Humid'}, 
							{color: _palette.color(),data: _seriesData[4],name: 'Temp'}, 
							{color: _palette.color(),data: _seriesData[5],name: 'Methane'}, 
							{color: _palette.color(),data: _seriesData[6],name: 'BTEX/VOX'}, 
			]
			buildall(thedata);
			bindresizeevent();
		};
		
		// PRIVATE METHODS: var private Method = function() {};
		var buildall = function (thedata) {
			buildhtml();
			buildgraph(thedata);
            buildui();
		}
		var bindresizeevent = function () {
			var waitForFinalEvent = (function () {
			var timers = {};
			return function (callback, ms, uniqueId) {
				if (!uniqueId) {
				uniqueId = _chartid;
				}
				if (timers[uniqueId]) {
				clearTimeout (timers[uniqueId]);
				}
				timers[uniqueId] = setTimeout(callback, ms);
			};
			})();
			jQuery(window).resize(function() {	
					waitForFinalEvent(function(){
						document.getElementById("chartblock"+_chartid).remove();
						buildall();
					}, 500, _chartid);
			});              
		}
		var buildhtml = function () {
			var form = ' \
				<form id="options" class="options"> \
					 \
					<div class="mainoptions"> \
						<section class="graphtypebuttons"> \
							<div id="renderer_form" class="toggler"> \
								<input type="radio" name="renderer" id="area" value="area" checked> \
								<label for="area">area</label> \
								<input type="radio" name="renderer" id="bar" value="bar"> \
								<label for="bar">bar</label> \
								<input type="radio" name="renderer" id="line" value="line"> \
								<label for="line">line</label> \
								<input type="radio" name="renderer" id="scatter" value="scatterplot"> \
								<label for="scatter">scatter</label> \
							</div> \
						</section> \
						<section class="offsetbuttons"> \
							<div id="offset_form"> \
								<label for="stack"><input type="radio" name="offset" id="stack" value="zero" checked><span>stack</span></label> \
								<label for="stream"><input type="radio" name="offset" id="stream" value="wiggle"><span>stream</span></label> \
								<label for="pct"><input type="radio" name="offset" id="pct" value="expand"><span>pct</span></label> \
								<label for="value"><input type="radio" name="offset" id="value" value="value"><span>value</span></label> \
							</div> \
							<div id="interpolation_form"> \
								<label for="cardinal"><input type="radio" name="interpolation" id="cardinal" value="cardinal" checked><span>cardinal</span></label> \
								<label for="linear"><input type="radio" name="interpolation" id="linear" value="linear"><span>linear</span></label> \
								<label for="step"><input type="radio" name="interpolation" id="step" value="step-after"><span>step</span></label> \
							</div> \
						</section> \
                    \
						<section class="smoother"><h6>Smoothing</h6><div id="smoother"></div></section> \
				    </div> \
					<section><div class="legend" id="'+_chartid+'_legend"></div></section> \
				</form> \
			';
			var htmlstructure = ' \
				<div class="chart_block" id="chartblock'+_chartid+'"> \
					'+form+' \
					<div class="display"> \
						<div id="'+_chartid+'"></div> \
						<div id="'+_chartid+'_timeline"></div> \
						<div id="'+_chartid+'_preview"></div> \
					</div> \
				</div> \
			';	
			var str =  htmlstructure;
			document.getElementById(_graphscontainer).insertAdjacentHTML( 'beforeend', str )
		}
		var buildgraph = function (thedata) {
          	var width = document.getElementById(_chartid).offsetWidth;
           	_graph = new Rickshaw.Graph( {
				element: document.getElementById(_chartid),
				width: width,
				height: _height,
				renderer: 'line',
				stroke: true,
				preserve: true,
				series: thedata
			});
			_graph.render();
		}
		var buildui = function (){			
			_preview = new Rickshaw.Graph.RangeSlider( { 
				graph: _graph,
				element: document.getElementById(_chartid+'_preview'),
			} );
			document.getElementById(_chartid+"_preview").style.width = "96%";
			document.getElementById(_chartid+"_preview").style.marginRight = "2%";
			document.getElementById(_chartid+"_preview").style.marginLeft = "2%";  
			var hoverDetail = new Rickshaw.Graph.HoverDetail( {
				graph: _graph,
				xFormatter: function(x) {
					return new Date(x * 1000).toString();
				}
			} );
			var annotator = new Rickshaw.Graph.Annotate( {
				graph: _graph,
				element: document.getElementById(_chartid+'_timeline')
			} );
			var legend = new Rickshaw.Graph.Legend( {
				graph: _graph,
				element: document.getElementById(_chartid+'_legend')

			} );
			var shelving = new Rickshaw.Graph.Behavior.Series.Toggle( {
				graph: _graph,
				legend: legend
			} );
			var order = new Rickshaw.Graph.Behavior.Series.Order( {
				graph: _graph,
				legend: legend
			} );
			var highlighter = new Rickshaw.Graph.Behavior.Series.Highlight( {
				graph: _graph,
				legend: legend
			} );
			var smoother = new Rickshaw.Graph.Smoother( {
				graph: _graph,
				element: document.querySelector('#smoother')
			} );
			var ticksTreatment = 'glow';
			var xAxis = new Rickshaw.Graph.Axis.Time( {
				graph: _graph,
				ticksTreatment: ticksTreatment,
				timeFixture: new Rickshaw.Fixtures.Time.Local()
			} );
			xAxis.render();
			var yAxis = new Rickshaw.Graph.Axis.Y( {
				graph: _graph,
				tickFormat: Rickshaw.Fixtures.Number.formatKMBT,
				ticksTreatment: ticksTreatment
			} );
			yAxis.render();
			var controls = new RenderControls( {
				element: document.querySelector('form'),
				graph: _graph
			} );
			/*
			var previewXAxis = new Rickshaw.Graph.Axis.Time({
				graph:_preview.previews[0],
				timeFixture: new Rickshaw.Fixtures.Time.Local(),
				ticksTreatment: ticksTreatment
			});
 			previewXAxis.render();
 			*/
		} 
    }
    return constructor;	
}();

