verion 1.1
Requirements:
There are dual screens is shared on a laptop – mouse click and a touch monitor for touch screen
2 operators can work together doing scoring at the same time

This code is added as a new tab and directly linked to the timers and detail on flagmachine local host 5000
List of sailors

Buttons and controls designed for 14 inch monitor size and large buttons for quick touch control
Maintain the sailor database and the selection for sign-on (ready to race, laoed onto the scoring sheet 

Functional spec
1)The scoring sheet is 4 columns, each column holds sailor Sailnumber (lager text), class, and in small text the sailor nickname
1)Group by classflag, count 3 groups with highest number of sailor and put the remainder into clans =‘Open’
 2) sortby lapcounter, seed: 
3) Scoring officer tallies the number of laps by clicking lap button, display the interger value. The finish is a tickbox, record time of tick.
4) Completed sailors is moved to bottom of the list and colour changed.
5) At any time the scoreing officer can move sailors up or down the list in a ranking


Once clarified, I'll:

Design database schema:

races (race_id, start_time, class_groups, status)
sailors (sailor_id, sail_number, class, nickname, status)
lap_records (sailor_id, race_id, lap_number, timestamp)
race_results (sailor_id, race_id, final_lap_count, finish_time, placement)
Create /finishsheet route serving new HTML template with 4-column layout
-important change name to finish sheet. (this app will not calculate scores, position and times only) - no longer use score or scoring


Add backend endpoints:

GET /api/sailors-for-onwater → grouped by class, sorted by seed
POST /api/record-lap → increment lap counter + update DB
POST /api/mark-finish → timestamp finish + move boat to completed
POST /api/reorder-sailors → manual ranking adjustments
Frontend (finishsheet.html + finishsheet.js):

4 responsive columns (touch-friendly buttons)
Real-time lap counter display
Finish checkbox with timestamp
Color change for completed boats
Drag/reorder capability
Link to flagmachine: Decide if countdown timer stays visible or is hidden in scoring mode - top banner, will have some info, - <div>elapsed time>

