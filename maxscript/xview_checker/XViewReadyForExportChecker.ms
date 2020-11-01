/*
 * Name: XView ReadyForExport Checker
 * Requirement: 3ds Max 2017
 */

(
global RfeChecker
local CN_RFE = "ReadyForExport Checker"	--checker name
struct RfeCheckerStruct
(
	mode = 1,
	cfgDialog = undefined,
	cfgFileName = (getDir #plugcfg +"\\XViewReadyForExportChecker.ini"),
	resultColors = #(red, red, red),

	fn check theTime theNode &theResults =
	(
		if (RfeChecker.mode == 1) and (classof theNode.material != MultiMaterial) then return 3
		
		bo = theNode.baseObject

		local theNumFaces = case classof bo of
		(
			Editable_Poly: polyop.GetNumfaces bo
			Editable_Mesh: bo.numfaces
		)
		
		if RfeChecker.mode == 1 then
		(
			local theMat = theNode.material
			local theMatSize = theMat.count
			local getFaceMatIDProc = case classof bo of
			(
				Editable_Poly: polyOp.getFaceMatID
				Editable_Mesh: getFaceMatID
			)
			for f = 1 to theNumFaces do
			(
				local matId = getFaceMatIDProc bo f
				if (matId > theMatSize) or (theMat[matId] == undefined) do append theResults f
			)
		)
		else if RfeChecker.mode == 2 then 
		(
			local getFaceSmoothGroupProc = case classof bo of
			(
				Editable_Poly: polyop.getFaceSmoothGroup
				Editable_Mesh: getFaceSmoothGroup
			)
			join theResults (for f = 1 to theNumFaces where (getFaceSmoothGroupProc bo f == 0) collect f)
		)
		else
		(
			local getFaceSmoothGroupProc = case classof bo of
			(
				Editable_Poly: polyop.getFaceSmoothGroup
				Editable_Mesh: getFaceSmoothGroup
			)
			
			for f = 1 to theNumFaces do
			(
				sg = getFaceSmoothGroupProc bo f
				sg_count = 0
				for i = 1 to 32 where (bit.get sg i) do 
				(
					sg_count += 1
					if sg_count > 1 then Exit
				)
				if sg_count > 1 then append theResults f
			)
		)
		--we return 3 because we stored the indices of the faces in the results array. 
		--the other options are 2 for edges, 1 for vertices and 0 if the check failed. 
		3
	),

	fn isSupported theNode =
	(
		(classof theNode.baseObject == Editable_Mesh or classof theNode.baseObject == Editable_Poly) -- or classof theNode == PolyMeshObject)
	),

	fn popupDlg =
	(
		try (destroyDialog RfeChecker.cfgDialog) catch()
		rollout cfgDialog CN_RFE
		(
			dropdownlist ddl_Mode width:140 align:#left offset:[-7,1] items:#("Material IDs","Missing Smooth Groups","Multiple Smooth Groups") selection:RfeChecker.mode across:2
			colorpicker clr_resultsColor fieldwidth:21 height:21 align:#right offset:[7,1] modal:true color:RfeChecker.resultColors[RfeChecker.mode]
			button btn_selectResults "Select Results" width:165 offset:[-1,0] _align:#right toolTip:"Only one object must be selected"

			fn updateDisplay =
			(
				XViewChecker.runCheck CurrentTime
				max views redraw
			)
			on ddl_Mode selected value do
			(
				RfeChecker.mode = value
				updateDisplay()
				RfeChecker.saveSetting "settings" "mode" value
				clr_resultsColor.color = RfeChecker.resultColors[value]
			)
			on clr_resultsColor changed value do 
			(
				RfeChecker.resultColors[RfeChecker.mode] = value
				max views redraw
				RfeChecker.saveSetting "colors" ("color_" + ddl_Mode.selection as string) RfeChecker.resultColors[RfeChecker.mode]
			)
			on btn_selectResults pressed do
			(
				subobjectLevel = 4
				XViewChecker.selectResults CurrentTime
				max views redraw
			)			
			on cfgDialog moved value do 
			(
				RfeChecker.saveSetting "dialog" "position" value
			)
			on cfgDialog close do
			(
				--nothing
			)
		)--end rollout
		
		local thePos = execute (getIniSetting RfeChecker.cfgFileName "dialog" "position")
		if classof thePos != Point2 do thePos = mouse.screenpos
		createDialog cfgDialog 178 60 thePos.x thePos.y
		RfeChecker.cfgDialog = cfgDialog
	),
	
	fn displayOverride theTime theNode theHwnd &theResults =
	(
		XViewChecker.displayResults RfeChecker.resultColors[RfeChecker.mode] theTime theNode theHwnd #Faces theResults
	),
	
	fn textOverride =
	(
		case RfeChecker.mode of
		(
			1: "Incorrect Mat IDs"
			2: "No Smoothing Group Selected"
			3: "Multiple Smoothing Group Selected"
		)
	),
	
	fn saveSetting section key value = 
	( 
		setIniSetting cfgFileName section key (value as string)
	)
)--end struct

try (destroyDialog RfeChecker.cfgDialog) catch()
RfeChecker = RfeCheckerStruct()

--load settings from INI file
local settintsToLoad = #(
	#("settings", "mode", &RfeChecker.mode, 0),
	#("colors", "color_1", RfeChecker.resultColors, 1),
	#("colors", "color_2", RfeChecker.resultColors, 2)
)
for s in settintsToLoad do
(
	local theVal = execute (getIniSetting RfeChecker.cfgFileName s[1] s[2])
	if theVal != OK do
	( if s[4] > 0 then s[3][s[4]] = theVal else *s[3] = theVal )
)--end s loop 

--register XView checkcer
XViewChecker.unRegisterChecker CN_RFE
XViewChecker.registerChecker RfeChecker.check RfeChecker.isSupported #Faces CN_RFE RfeChecker.popupDlg undefined RfeChecker.displayOverride
)--end script