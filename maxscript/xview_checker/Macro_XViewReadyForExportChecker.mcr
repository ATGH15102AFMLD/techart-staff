/*
 * Name: MacroScript for XView ReadyForExport Checker
 * Requirement: 3ds Max 2017, XViewReadyForExportChecker.ms
 */

MacroScript xView_ReadyForExport_Checker
            ButtonText:"ReadyForExport"
            category:"xView"
            internalCategory:"xView"
            Tooltip:"ReadyForExport Checker Display Mode"
(
local CN_RFE = "ReadyForExport Checker"	--checker name

on isChecked return 
    try
    (
        xViewChecker.getCheckerName xViewChecker.activeIndex == CN_RFE and xViewChecker.on == true
    )
    catch()
    
on execute do 
    try
    (
        if (xViewChecker.getCheckerName xViewChecker.activeIndex == CN_RFE and xViewChecker.on == true)
        then
            xViewChecker.On = False
        else
        (	
            local theIndex = 0
            for i = 1 to xViewChecker.getNumCheckers() do
              if xViewChecker.getCheckerName i == CN_RFE do theIndex = i
            if theIndex > 0 do  
            (
              xViewChecker.setActiveCheckerID(xViewChecker.getCheckerID theIndex)
              xViewChecker.on = true
            )
        )
    )	
    catch()	
	 
)--end MacroScript