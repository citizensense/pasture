/*
	 Object structure derived from comment 54 in: 
	 http://stackoverflow.com/questions/1595611/how-to-properly-create-a-custom-object-in-javascript
*/
var Graphkit = function (){

	var constructor = function (chartid, height, seriesData, rolloverstring) {
		
		// PRIVATE VARS
		var _chartid = chartid;
		var _height =  height;
		var _seriesData = seriesData;
		var _palette = new Rickshaw.Color.Palette( { scheme: 'colorwheel' } );
		var _graph;
        var _graphscontainer = "charts"; // should be an element id
		var _preview;
		var _rolloverstring = rolloverstring;
		var _hoverpos;
		var _annotations;
		var _subcounter = 0;
		var _sublock;

		// PUBLIC METHODS: this.publicMethod = function() {};
		this.build = function (data, annotations){
			_annotations = annotations;
		    // Colorise the lines
		    for (i = 0; i < data.length; i++) {
                data[i]['color'] = _palette.color(); 
		    }
		    // Then build the graph
            buildall(data);
            bindresizeevent();
        }
        
        // Method to generate test data
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
            buildclickevents();
        }
		var buildclickevents = function () {
			// Add a click event to the graph
			var graphdiv = _chartid+'_graph'; 
        	var graph = document.getElementById(graphdiv);
        	graph.addEventListener('click',function (e) {
        		// Populate the form field with the timecode
        		var fieldid = _chartid+'_timecode';
        		var field = document.getElementById(fieldid);
        		field.value = _hoverpos;
        		var form = document.getElementById(_chartid+'_anoform');
				form.style.display = 'block';
				var formbutton = document.getElementById(_chartid+'_submitanno');
				var dateobj = new Date(_hoverpos*1000);
				var date = dateobj.toUTCString();
				formbutton.value = 'Create annotation for:\n'+date;
			},true);
			// Lets sort the close button
			var closebutton = document.getElementById(_chartid+'_close'); 
			closebutton.addEventListener('click',function (e) {
				var form = document.getElementById(_chartid+'_anoform'); 
				form.style.display = 'none';
			},true);
			// Construct the edit button functionality
			var editbuts = document.getElementsByClassName(_chartid+'_anoeditclass');	
			for (i=0;i<editbuts.length;i++){
				editbuts[i].addEventListener('click',function (e) {
					var form = document.getElementById(_chartid+'_anoform');
					var text = document.getElementById(_chartid+'_text');
					aid = this.id.replace('aid', '');
					for (n=0;n<_annotations.length;n++){
						if(_annotations[n][0]==aid){
							text.value=_annotations[n][2];
							document.getElementById(_chartid+'_update').value = aid;
							document.getElementById(_chartid+'_submitanno').value='Update annotation';
							document.getElementById(_chartid+'_anoform').method = 'PUT';
						}
					}
					form.style.display = 'block';
				});
			}
			// Now lets submit the form and override the default action
			var submitid = _chartid+'_submitanno'; 
			var submit = document.getElementById(submitid);
			submit.addEventListener('click',function (e) {
				e.preventDefault();
				aid = document.getElementById(_chartid+'_update').value;
				// Lets check if the update field has been populated, if so, the PUT
				if(aid!=''){					
					submitme('POST', '/api/update/'+aid);
				// Otherise just POST
				}else{
					submitme('POST', '/api');
				}
			},true);   
		}
		// Build a form submission and response
		var submitme = function(method, url) { // POST, GET, DELETE
			// Lets hide the form and wait
    		var form = document.getElementById(_chartid+'_anoform'); 
			form.display = 'none';
			var XHR = new XMLHttpRequest();
    		// We bind the FormData object and the form element
    		var FD  = new FormData(form);
    		// We define what will happen if the data is successfully sent
    		XHR.addEventListener("load", function(event) {
				try {
					jsonresp = JSON.parse(event.target.responseText);
				}catch(e){
					jsonresp = false;
				}
				if(jsonresp!=false){
					// If all ok, lets add the new annotation
					if(jsonresp['code']=='OK'){
						var text = document.getElementById(_chartid+'_text');
						annotator.add(_hoverpos, text.value);
						annotator.update();
						text.value = '';
						var form = document.getElementById(_chartid+'_anoform');   
						var session = document.getElementById(_chartid+'_sessionid');
						session.value = jsonresp['sessionid']
						form.style.display = 'none';
						// hide the form fields
						var loginfields = document.getElementsByClassName(_chartid+'_hideuser');	
						for (i=0;i<loginfields.length;i++){
								loginfields[i].style.display = 'none';
						}
						alert(jsonresp['msg']);
					}else{
						alert('Error. Couldn\'t unerstand repsonse from server: '+event.target.responseText);
						form.display = 'block';
					}
				}
    		});
    		// We define what will happen in case of error
    		XHR.addEventListener("error", function(event) {
      			alert('Sorry! Unable to submit form. Possible server error.');
				form.display = 'block';
    		});
    		// We setup our request
    		XHR.open(method, url);
    		XHR.send(FD);
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
						<section class="smoother"><h6>Smoothing</h6><div id="smoother"></div></section> \
				    </div> \
					<section><div class="legend" id="'+_chartid+'_legend"></div></section> \
				</form> \
			';
			var annotationform = ' \
				<iframe style="display:none;" name="'+_chartid+'_iframe" id="'+_chartid+'_iframer"></iframe> \
				<form class="addannotationform" id="'+_chartid+'_anoform" action="/api" method="POST" target="'+_chartid+'_iframe">   \
					<a href="#" class="annoclose" id="'+_chartid+'_close" >close [X]</a> \
					<input type="hidden" name="timecode" id="'+_chartid+'_timecode"/> \
					<input type="hidden" name="chartid" value="'+_chartid+'" id="'+_chartid+'_chartid"/> \
					<label class="'+_chartid+'_hideuser">Username</label> \
					<input class="'+_chartid+'_hideuser" type="text" name="username" value="admin" id="'+_chartid+'_username"/> \
					<label class="'+_chartid+'_hideuser">password</label> \
					<input class="'+_chartid+'_hideuser" type="text" name="password" value="carbon31" id="'+_chartid+'_password"/> \
					<input type="hidden" name="sessionid" value="" id="'+_chartid+'_sessionid"/> \
					<input type="text" name="update" value="" id="'+_chartid+'_update"/> \
					<label>Text</label> \
					<textarea rows="4" name="annotation" id="'+_chartid+'_text"> </textarea>   \
					<input type="submit" class="anosubmit" id="'+_chartid+'_submitanno" value="Create annotation" /> \
				</form> \
			';
			var htmlstructure = ' \
				<div class="chart_block" id="chartblock'+_chartid+'"> \
					'+annotationform+' \
					'+form+' \
					<div class="display"> 	\
						<div id="'+_chartid+'_graph"></div> \
						<div id="'+_chartid+'_timeline"></div> \
						<div id="'+_chartid+'_preview"></div> \
					</div> \
				</div> \
			';
			var str =  htmlstructure;
			document.getElementById(_graphscontainer).insertAdjacentHTML('beforeend', str)
		}
		var buildgraph = function (thedata) {
			var graphdiv = _chartid+'_graph'; // _chartid
          	var width = document.getElementById(graphdiv).offsetWidth;
           	_graph = new Rickshaw.Graph( {
				element: document.getElementById(graphdiv),
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
					timecode = x * 1000;
					_hoverpos = timecode/1000;
					dateobj = new Date(timecode);
					date = dateobj.toDateString()+dateobj.toUTCString();
					return date;
				}
			} );
			annotator = new Rickshaw.Graph.Annotate( {
				graph: _graph,
				element: document.getElementById(_chartid+'_timeline')
			} );
			// Add annotations to the graph
			for (i = 0; i < _annotations.length; i++) {
				var aid = _annotations[i][0];
				var timestamp = _annotations[i][1];  
				var text = _annotations[i][2];
				annotator.add(timestamp, '<a class="anoedit '+_chartid+'_anoeditclass" id="aid'+aid+'">edit</a>'+text);
			}
			annotator.update();
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
			var ticksTreatment = '';
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

