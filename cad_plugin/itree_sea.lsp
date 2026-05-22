;;; ===================================================================
;;; itree_sea.lsp — AutoCAD / BricsCAD AutoLISP Wrapper
;;; ===================================================================
;;;
;;; Registers the ITREESEA command in AutoCAD/BricsCAD.
;;; When executed, it saves the current drawing as DXF (if needed),
;;; calls the Python i-Tree SEA CAD plugin, and opens the output CSV.
;;;
;;; Installation:
;;;   1. Copy this file to your AutoCAD support path.
;;;   2. Load it: (load "itree_sea.lsp")
;;;   3. Run: ITREESEA
;;;
;;; Or add to acaddoc.lsp / on_doc_load.lsp for auto-loading.
;;; ===================================================================

(defun c:ITREESEA (/ dxf-path py-script out-dir cmd)
  (princ "\n=== i-Tree SEA — Tree Carbon Calculator ===\n")

  ;; Get the DXF path (export current drawing if needed)
  (setq dxf-path (strcat (getvar "DWGPREFIX")
                          (vl-filename-base (getvar "DWGNAME"))
                          ".dxf"))

  ;; Check if DXF exists or prompt to save
  (if (not (findfile dxf-path))
    (progn
      (princ "\nExporting current drawing to DXF...")
      (command "._DXFOUT" dxf-path "V" "2018" "")
    )
  )

  ;; Set paths — update these to match your installation
  (setq py-script "C:\\itree-sea\\cad_plugin\\itree_sea_cad.py")
  (setq out-dir   (strcat (getvar "DWGPREFIX") "itree_output"))

  ;; Build the command
  (setq cmd (strcat "python \""
                     py-script
                     "\" process --input \""
                     dxf-path
                     "\" --output \""
                     out-dir
                     "\" --years 25"))

  (princ (strcat "\nRunning: " cmd "\n"))

  ;; Execute
  (command "._SHELL" cmd)

  ;; Open output
  (princ (strcat "\n✓ Results saved to: " out-dir "\n"))
  (princ "\nUse ITREESEA_OPEN to view the schedule CSV.\n")
  (princ)
)

;;; Open the generated schedule CSV in the default application
(defun c:ITREESEA_OPEN (/ csv-path)
  (setq csv-path (strcat (getvar "DWGPREFIX")
                          "itree_output\\planting_schedule.csv"))
  (if (findfile csv-path)
    (progn
      (startapp "explorer" csv-path)
      (princ (strcat "\nOpened: " csv-path "\n"))
    )
    (princ "\nSchedule CSV not found. Run ITREESEA first.\n")
  )
  (princ)
)

(princ "\ni-Tree SEA loaded. Commands: ITREESEA, ITREESEA_OPEN\n")
(princ)
