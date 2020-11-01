/*
 * Name: Align Body and Head vertices positions and normals along a seam
 * Requirement: 3ds Max 2017
 */
 
(
	local cfgFileName = (getDir #plugcfg +"\\HeadNBody.ini")
	local rolloutName = "Head'N'Body"
	local EPSILON = 0.005
	
	-- Return array of selected vertices indexes from Editable Poly selected edges
	fn getSelectedEdgesVerts obj = (
		verts = #()
		edges = polyop.getEdgeSelection obj.baseObject as array
		print edges.count
		for i = 1 to edges.count do 
		(
			edgeVerts = polyop.getEdgeVerts obj.baseObject edges[i]
			appendIfUnique verts edgeVerts[1]
			appendIfUnique verts edgeVerts[2]
		)
		return verts
	)
	
	-- Get Normals indexes from vertices indexes and set it's to explicit
	-- return Normals indexes
	fn getVertexNormals modEditNormals vertexIndexes = (
		result = #()
		all_normals = #{}
		for i = 1 to vertexIndexes.count do (
			-- get vertex normals indexes
			verts = #{vertexIndexes[i]}
			normals = #{}
			modEditNormals.ConvertVertexSelection &verts &normals
			-- suppose all normals equals
			i = (normals as array)[1]
			append result (modEditNormals.GetNormal i)
			
			join all_normals normals
		)
		-- Set normals explicit
		modEditNormals.Select all_normals
		modEditNormals.MakeExplicit()
		modEditNormals.SetSelection #{}
		
		return result
	)
	
	fn setVertexNormals obj modEditNormals vertexIndexes normalsValues = (
		select obj
		modPanel.setCurrentObject modEditNormals

		--format "setVertexNormals % %\n" vertexIndexes.count normalsValues.count
		
		for i = 1 to vertexIndexes.count do (
			-- get vertex normals indexes
			verts = #{vertexIndexes[i]}
			normals = #{}
			modEditNormals.ConvertVertexSelection &verts &normals
			-- suppose all normals equals
			idx = (normals as array)[1]
			modEditNormals.SetNormal idx normalsValues[i]
		)

		maxOps.CollapseNodeTo obj (obj.modifiers.count) true
	)	
	
	fn alignSeam obj1 obj2 = (
		-- Some check
		if obj1 == undefined or obj2 == undefined then return "Pick two objects"
		if classof obj1.baseObject != Editable_Poly \
			or classof obj2.baseObject != Editable_Poly then return "Support only Editable Poly objects"	
		if obj1 == obj2 then return "Pick different objects"
		
		-- Collect selected vertices index
		verts_1 = getSelectedEdgesVerts obj1
		verts_2 = getSelectedEdgesVerts obj2
		
		if verts_1.count == 0 then return "Select edges for object [1]"
		if verts_2.count == 0 then return "Select edges for object [2]"
		
		format "Founded vertices [1]:% and [2]:%\n" verts_1.count verts_2.count
		
		o1 = obj1.baseObject
		o2 = obj2.baseObject

		-- Find vertices pairs
		pairs = #(#(), #())
		for i = 1 to verts_1.count do (
			for j = 1 to verts_2.count do (
				i_1 = verts_1[i]
				i_2 = verts_2[j]
				pos_1 = polyop.getVert o1 i_1
				pos_2 = polyop.getVert o2 i_2
				if distance pos_1 pos_2 < EPSILON then (
					append pairs[1] i_1
					append pairs[2] i_2
					deleteItem verts_2 j
					Exit
				)
			)
		)
		format "Founded vertices pairs: %\n" pairs[1].count
		
		-- Align positions
		for i = 1 to pairs[1].count do
		(
			pos_1 = polyop.getVert o1 pairs[1][i]
			pos_2 = polyop.getVert o2 pairs[2][i]
			aligned_pos = (pos_1 + pos_2) / 2.0
			polyop.setVert o1 pairs[1][i] aligned_pos
			polyop.setVert o2 pairs[2][i] aligned_pos
		)
		format "Positions aligned\n"
		
		-- Align normals
		max modify mode
		
		select obj1
		med1 = edit_Normals()
		med1.displayLength = 0.2
		addModifier obj1 med1 before:obj1.modifiers.count
		modPanel.setCurrentObject med1
		norms_1 = getVertexNormals med1 pairs[1]
		
		select obj2
		med2 = edit_Normals()
		med2.displayLength = 0.2
		addModifier obj2 med2 before:obj2.modifiers.count
		modPanel.setCurrentObject med2
		norms_2 = getVertexNormals med2 pairs[2]
		
		format "Founded normals [1]:% and [2]:%\n" norms_1.count norms_2.count

		-- Calc average normals
		norms_avg = #()
		for i = 1 to norms_1.count do 
		( 
			append norms_avg ((norms_1[i] + norms_2[i]) / 2.0)
		)
		
		format "Average normals count: %\n" norms_avg.count
		
		-- Update normals
		setVertexNormals obj1 med1 pairs[1] norms_avg
		setVertexNormals obj2 med2 pairs[2] norms_avg
		
		format "Normals aligned\n"
		
		return Ok
	)
	
	rollout dlgHeadNBody rolloutName (
		label lbl_one "[1] object:" align:#left
		pickbutton btn_one "..." message:"Pick first object" autoDisplay:true width:180
		label lbl_two "[2] object:" align:#left
		pickbutton btn_two "..." message:"Pick second object" autoDisplay:true width:180
		
		label lbl_actions "Actions:" align:#left
		--button btn_action1 "Base head to [1]" width:180
		button btn_action2 "Align seam [1] & [2]" width:180
		
		on btn_action2 pressed do (
			disableSceneRedraw()
			try (
				msg = alignSeam btn_one.object btn_two.object
			) catch ()
			enableSceneRedraw()
			redrawViews()
			if msg != Ok then (
				messageBox msg title:rolloutName beep:true 
			)
		)
		
		on dlgHeadNBody moved value do 
		(
			setIniSetting cfgFileName "dialog" "position" (value as string)
		)
	)
	local thePos = execute (getIniSetting cfgFileName "dialog" "position")
	if classof thePos != Point2 do thePos = mouse.screenpos
	createDialog dlgHeadNBody 200 200 thePos.x thePos.y
)