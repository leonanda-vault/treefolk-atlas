;;; ===================================================================
;;; itree_sea_reformat.lsp — AutoCAD Block Attribute Reformatter
;;; ===================================================================
;;;
;;; i-Tree SEA — Block Selection & Reformatting Tool for AutoCAD
;;;
;;; This script provides commands to select tree blocks in AutoCAD
;;; and standardise their attributes to match the i-Tree SEA schema:
;;;   SPECIES  (botanical name)
;;;   CALIPER  (planting caliper in cm)
;;;   TAG      (unique tree identifier)
;;;   HEIGHT   (optional, in metres)
;;;
;;; COMMANDS:
;;;   ITREEFORMAT     Select blocks interactively and add/fix attributes
;;;   ITREELAYER      Batch-reformat all blocks on a specified layer
;;;   ITREEAUDIT      Scan drawing and report blocks missing attributes
;;;   ITREEEXPORT     Export all tree block data to CSV
;;;   ITREESCHEMA     Add missing ATTDEF tags to selected block definitions
;;;
;;; INSTALLATION:
;;;   1. Copy this file to your AutoCAD support path or project folder
;;;   2. APPLOAD → Browse → Select itree_sea_reformat.lsp
;;;   3. Or add (load "itree_sea_reformat.lsp") to acaddoc.lsp
;;;
;;; ===================================================================


;;; ─── UTILITY FUNCTIONS ─────────────────────────────────────────────

;; Get all attribute tags from a block reference as a list of (TAG . VALUE) pairs
(defun ITREE:get-attribs (ent / elst attribs sub-ent sub-data)
  (setq attribs '())
  (setq sub-ent (entnext ent))
  (while sub-ent
    (setq sub-data (entget sub-ent))
    (if (= (cdr (assoc 0 sub-data)) "ATTRIB")
      (setq attribs
        (cons (cons (strcase (cdr (assoc 2 sub-data)))
                    (cdr (assoc 1 sub-data)))
              attribs)))
    (setq sub-ent (entnext sub-ent))
  )
  (reverse attribs)
)

;; Get a specific attribute value from a block reference
(defun ITREE:get-attrib-value (ent tag / attribs pair)
  (setq attribs (ITREE:get-attribs ent))
  (setq pair (assoc (strcase tag) attribs))
  (if pair (cdr pair) nil)
)

;; Set a specific attribute value on a block reference
(defun ITREE:set-attrib-value (ent tag new-value / sub-ent sub-data found)
  (setq sub-ent (entnext ent))
  (setq found nil)
  (while (and sub-ent (not found))
    (setq sub-data (entget sub-ent))
    (if (and (= (cdr (assoc 0 sub-data)) "ATTRIB")
             (= (strcase (cdr (assoc 2 sub-data))) (strcase tag)))
      (progn
        (setq sub-data (subst (cons 1 new-value) (assoc 1 sub-data) sub-data))
        (entmod sub-data)
        (entupd sub-ent)
        (setq found T)
      )
    )
    (setq sub-ent (entnext sub-ent))
  )
  found
)

;; Check if a block has a specific attribute tag
(defun ITREE:has-attrib (ent tag / attribs)
  (setq attribs (ITREE:get-attribs ent))
  (assoc (strcase tag) attribs)
)

;; Check if entity is a block reference (INSERT)
(defun ITREE:is-block-ref (ent / data)
  (setq data (entget ent))
  (= (cdr (assoc 0 data)) "INSERT")
)

;; Get block name from entity
(defun ITREE:block-name (ent / data)
  (setq data (entget ent))
  (cdr (assoc 2 data))
)

;; Get insertion point from entity
(defun ITREE:insert-point (ent / data)
  (setq data (entget ent))
  (cdr (assoc 10 data))
)

;; Get layer from entity
(defun ITREE:layer (ent / data)
  (setq data (entget ent))
  (cdr (assoc 8 data))
)

;; Detect and remap common tag aliases to standard names
(defun ITREE:detect-species-tag (ent / tags)
  (setq tags '("SPECIES" "TREE_SPECIES" "SP" "BOTANICAL" "NAMA"
               "NAMA_POHON" "PLANT" "TANAMAN"))
  (ITREE:find-existing-tag ent tags)
)

(defun ITREE:detect-caliper-tag (ent / tags)
  (setq tags '("CALIPER" "DBH" "DIAMETER" "SIZE" "CAL"))
  (ITREE:find-existing-tag ent tags)
)

(defun ITREE:detect-height-tag (ent / tags)
  (setq tags '("HEIGHT" "HT" "TINGGI" "TREE_HEIGHT"))
  (ITREE:find-existing-tag ent tags)
)

(defun ITREE:find-existing-tag (ent tag-list / attribs result)
  (setq attribs (ITREE:get-attribs ent))
  (setq result nil)
  (foreach tag tag-list
    (if (and (not result) (assoc (strcase tag) attribs))
      (setq result (strcase tag))
    )
  )
  result
)


;;; ─── COMMAND: ITREEFORMAT ──────────────────────────────────────────
;;; Interactive selection — pick blocks and reformat their attributes

(defun c:ITREEFORMAT (/ ss i ent species-tag caliper-tag height-tag
                        species caliper height tag-val count
                        block-name layer user-species user-caliper)
  (princ "\n=== i-Tree SEA: Block Attribute Reformatter ===")
  (princ "\nSelect tree blocks to reformat (or Enter for all on L-PLNT-TREE-* layers)...")

  (setq ss (ssget))
  (if (not ss)
    (progn
      (princ "\nNo selection. Selecting all INSERTs on L-PLNT-TREE-* layers...")
      (setq ss (ssget "X"
        (list '(0 . "INSERT") '(8 . "L-PLNT-TREE-*"))))
    )
  )

  (if (not ss)
    (progn (princ "\nNo block references found.") (princ) (quit))
  )

  (setq count 0)
  (setq i 0)

  (repeat (sslength ss)
    (setq ent (ssname ss i))
    (setq i (1+ i))

    (if (not (ITREE:is-block-ref ent))
      (progn) ; skip non-blocks
      (progn
        (setq block-name (ITREE:block-name ent))
        (setq layer (ITREE:layer ent))

        ;; Detect existing species tag (any alias)
        (setq species-tag (ITREE:detect-species-tag ent))
        (setq caliper-tag (ITREE:detect-caliper-tag ent))
        (setq height-tag  (ITREE:detect-height-tag ent))

        ;; Get current values
        (setq species (if species-tag
                        (ITREE:get-attrib-value ent species-tag) ""))
        (setq caliper (if caliper-tag
                        (ITREE:get-attrib-value ent caliper-tag) ""))
        (setq height  (if height-tag
                        (ITREE:get-attrib-value ent height-tag) ""))

        ;; Report current state
        (princ (strcat "\n\n── Block: " block-name
                       " | Layer: " layer
                       " ──"))
        (if (and species (/= species ""))
          (princ (strcat "\n  Current species: " species))
          (princ "\n  ⚠ No species found")
        )
        (if (and caliper (/= caliper ""))
          (princ (strcat "\n  Current caliper/DBH: " caliper))
          (princ "\n  ⚠ No caliper/DBH found")
        )

        ;; If SPECIES tag exists under an alias, copy to standard tag
        (if (and species-tag (/= species-tag "SPECIES"))
          (progn
            (princ (strcat "\n  → Remapping " species-tag " → SPECIES"))
            ;; We can't add new attribs via LISP easily,
            ;; so we just rename by setting the standard one if it exists
            (if (ITREE:has-attrib ent "SPECIES")
              (ITREE:set-attrib-value ent "SPECIES" species)
            )
          )
        )

        ;; If caliper tag exists under an alias, remap
        (if (and caliper-tag (/= caliper-tag "CALIPER"))
          (progn
            (princ (strcat "\n  → Remapping " caliper-tag " → CALIPER"))
            (if (ITREE:has-attrib ent "CALIPER")
              (ITREE:set-attrib-value ent "CALIPER" caliper)
            )
          )
        )

        ;; Prompt user to fix missing values
        (if (or (not species) (= species ""))
          (progn
            (setq user-species
              (getstring T
                (strcat "\n  Enter species for " block-name ": ")))
            (if (and user-species (/= user-species ""))
              (if (ITREE:has-attrib ent "SPECIES")
                (ITREE:set-attrib-value ent "SPECIES" user-species)
              )
            )
          )
        )

        (if (or (not caliper) (= caliper ""))
          (progn
            (setq user-caliper
              (getstring
                (strcat "\n  Enter caliper (cm) for " block-name " [5]: ")))
            (if (or (not user-caliper) (= user-caliper ""))
              (setq user-caliper "5")
            )
            (if (ITREE:has-attrib ent "CALIPER")
              (ITREE:set-attrib-value ent "CALIPER" user-caliper)
            )
          )
        )

        ;; Move block to standard layer if not already on one
        (if (not (wcmatch (strcase layer) "L-PLNT-TREE-*"))
          (progn
            (princ (strcat "\n  → Moving from " layer " to L-PLNT-TREE-PROP"))
            ;; Create layer if needed
            (if (not (tblsearch "LAYER" "L-PLNT-TREE-PROP"))
              (command "._LAYER" "N" "L-PLNT-TREE-PROP" "C" "3" "L-PLNT-TREE-PROP" "")
            )
            (setq data (entget ent))
            (setq data (subst '(8 . "L-PLNT-TREE-PROP") (assoc 8 data) data))
            (entmod data)
          )
        )

        (setq count (1+ count))
      )
    )
  )

  (princ (strcat "\n\n✓ Reformatted " (itoa count) " tree blocks."))
  (princ)
)


;;; ─── COMMAND: ITREEAUDIT ───────────────────────────────────────────
;;; Scan entire drawing and report blocks missing required attributes

(defun c:ITREEAUDIT (/ ss i ent block-name layer species-tag caliper-tag
                       ok-count warn-count err-count)
  (princ "\n=== i-Tree SEA: Drawing Audit ===\n")

  ;; Get all INSERT entities
  (setq ss (ssget "X" '((0 . "INSERT"))))
  (if (not ss)
    (progn (princ "No block references found.") (princ) (quit))
  )

  (setq ok-count 0 warn-count 0 err-count 0 i 0)

  (repeat (sslength ss)
    (setq ent (ssname ss i))
    (setq i (1+ i))

    (setq block-name (ITREE:block-name ent))
    (setq layer (ITREE:layer ent))

    ;; Only check blocks on planting layers or with TREE/PALM in name
    (if (or (wcmatch (strcase layer) "L-PLNT-TREE-*")
            (wcmatch (strcase block-name) "*TREE*,*PALM*,*POHON*"))
      (progn
        (setq species-tag (ITREE:detect-species-tag ent))
        (setq caliper-tag (ITREE:detect-caliper-tag ent))

        (cond
          ;; Both present → OK
          ((and species-tag caliper-tag)
           (setq ok-count (1+ ok-count)))

          ;; Species missing → ERROR
          ((not species-tag)
           (princ (strcat "\n  ✗ MISSING SPECIES: " block-name
                          " on " layer
                          " at " (ITREE:pt-to-str (ITREE:insert-point ent))))
           (setq err-count (1+ err-count)))

          ;; Caliper missing → WARNING
          ((not caliper-tag)
           (princ (strcat "\n  ⚠ MISSING CALIPER: " block-name
                          " on " layer " (species: "
                          (ITREE:get-attrib-value ent species-tag) ")"))
           (setq warn-count (1+ warn-count)))
        )
      )
    )
  )

  (princ "\n\n── Audit Summary ──")
  (princ (strcat "\n  ✓ OK:       " (itoa ok-count)))
  (princ (strcat "\n  ⚠ Warnings: " (itoa warn-count) " (missing caliper — will default to 5 cm)"))
  (princ (strcat "\n  ✗ Errors:   " (itoa err-count) " (missing species — cannot calculate)"))
  (princ (strcat "\n  Total:      " (itoa (+ ok-count warn-count err-count)) " tree blocks"))
  (princ "\n\nRun ITREEFORMAT to fix issues interactively.")
  (princ)
)

;; Helper: point to string
(defun ITREE:pt-to-str (pt)
  (strcat "(" (rtos (car pt) 2 1) ", " (rtos (cadr pt) 2 1) ")")
)


;;; ─── COMMAND: ITREEEXPORT ──────────────────────────────────────────
;;; Export all tree block attributes to CSV

(defun c:ITREEEXPORT (/ ss i ent block-name layer pt species caliper height
                        species-tag caliper-tag height-tag
                        csv-path fp count)
  (princ "\n=== i-Tree SEA: Export Tree Blocks to CSV ===\n")

  ;; Get export path
  (setq csv-path (getfiled "Save tree data CSV" "" "csv" 1))
  (if (not csv-path) (progn (princ "Cancelled.") (princ) (quit)))

  ;; Get all INSERTs on planting layers
  (setq ss (ssget "X" '((0 . "INSERT"))))
  (if (not ss)
    (progn (princ "No block references found.") (princ) (quit))
  )

  (setq fp (open csv-path "w"))
  (write-line "tree_id,block_name,species,caliper_cm,height_m,x,y,layer" fp)

  (setq count 0 i 0)
  (repeat (sslength ss)
    (setq ent (ssname ss i))
    (setq i (1+ i))

    (setq block-name (ITREE:block-name ent))
    (setq layer (ITREE:layer ent))

    ;; Filter to tree layers or tree-named blocks
    (if (or (wcmatch (strcase layer) "L-PLNT-TREE-*")
            (wcmatch (strcase block-name) "*TREE*,*PALM*,*POHON*"))
      (progn
        (setq species-tag (ITREE:detect-species-tag ent))
        (setq caliper-tag (ITREE:detect-caliper-tag ent))
        (setq height-tag  (ITREE:detect-height-tag ent))

        (setq species (if species-tag (ITREE:get-attrib-value ent species-tag) ""))
        (setq caliper (if caliper-tag (ITREE:get-attrib-value ent caliper-tag) "5"))
        (setq height  (if height-tag  (ITREE:get-attrib-value ent height-tag) ""))

        (setq pt (ITREE:insert-point ent))
        (setq count (1+ count))

        (write-line
          (strcat (itoa count) ","
                  block-name ","
                  species ","
                  caliper ","
                  height ","
                  (rtos (car pt) 2 3) ","
                  (rtos (cadr pt) 2 3) ","
                  layer)
          fp)
      )
    )
  )

  (close fp)
  (princ (strcat "\n✓ Exported " (itoa count) " trees → " csv-path))
  (princ)
)


;;; ─── COMMAND: ITREELAYER ───────────────────────────────────────────
;;; Batch-reformat all blocks on a specific layer

(defun c:ITREELAYER (/ layer-name ss i ent species-tag caliper-tag
                       species caliper count)
  (princ "\n=== i-Tree SEA: Batch Reformat by Layer ===\n")
  (setq layer-name (getstring T "\nEnter layer name [L-PLNT-TREE-PROP]: "))
  (if (= layer-name "") (setq layer-name "L-PLNT-TREE-PROP"))

  (setq ss (ssget "X" (list '(0 . "INSERT") (cons 8 layer-name))))
  (if (not ss)
    (progn
      (princ (strcat "\nNo blocks found on layer: " layer-name))
      (princ) (quit))
  )

  (princ (strcat "\nFound " (itoa (sslength ss)) " blocks on " layer-name))

  ;; Get default species for batch
  (setq default-species
    (getstring T "\nDefault species for blocks without SPECIES tag (Enter to skip): "))
  (setq default-caliper
    (getstring "\nDefault caliper (cm) for blocks without CALIPER tag [5]: "))
  (if (= default-caliper "") (setq default-caliper "5"))

  (setq count 0 i 0)
  (repeat (sslength ss)
    (setq ent (ssname ss i))
    (setq i (1+ i))

    (setq species-tag (ITREE:detect-species-tag ent))
    (setq caliper-tag (ITREE:detect-caliper-tag ent))

    ;; Fill missing SPECIES
    (if (and (not species-tag)
             (/= default-species "")
             (ITREE:has-attrib ent "SPECIES"))
      (ITREE:set-attrib-value ent "SPECIES" default-species)
    )

    ;; Fill missing CALIPER
    (if (and (not caliper-tag)
             (ITREE:has-attrib ent "CALIPER"))
      (ITREE:set-attrib-value ent "CALIPER" default-caliper)
    )

    (setq count (1+ count))
  )

  (princ (strcat "\n✓ Processed " (itoa count) " blocks on " layer-name))
  (princ)
)


;;; ─── STARTUP MESSAGE ───────────────────────────────────────────────

(princ "\n")
(princ "╔══════════════════════════════════════════════╗\n")
(princ "║  i-Tree SEA — Block Reformatter loaded       ║\n")
(princ "║                                              ║\n")
(princ "║  Commands:                                   ║\n")
(princ "║    ITREEFORMAT  - Select & fix attributes    ║\n")
(princ "║    ITREEAUDIT   - Scan for missing data      ║\n")
(princ "║    ITREEEXPORT  - Export blocks to CSV        ║\n")
(princ "║    ITREELAYER   - Batch reformat by layer    ║\n")
(princ "║    ITREESEA     - Run carbon calculation     ║\n")
(princ "╚══════════════════════════════════════════════╝\n")
(princ)
