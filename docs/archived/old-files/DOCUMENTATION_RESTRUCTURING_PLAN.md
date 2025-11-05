# Documentation Restructuring Plan

## 📊 Current State
- **Total files:** 67 Markdown documentation files
- **Main files:** README.md, CHANGELOG.md, ROADMAP.md
- **Duplicates:** 13 SUMMARY files, 10 NFT-related files, 4 README variants
- **Languages:** Russian and English (mixed)

## 🎯 Target Structure

### Core Documentation (Root Directory)
```
├── README.md                    # ✅ Updated - Main project overview
├── CHANGELOG.md                  # ✅ Updated - Version history
├── ROADMAP.md                    # ✅ Updated - Development roadmap
├── CONTRIBUTING.md               # 📋 To create - Contribution guidelines
├── LICENSE                       # ✅ Exists
└── .env.example                  # ✅ Exists - Configuration template
```

### docs/ Directory (Organized)
```
docs/
├── README.md                     # Index of all documentation
├── api/
│   ├── README.md                 # API overview
│   ├── endpoints.md              # All API endpoints (from API_DOCUMENTATION.md)
│   └── examples.md               # Usage examples (from API_EXAMPLES_RU.md)
├── guides/
│   ├── installation.md           # From INSTALLATION_GUIDE_RU.md
│   ├── user-guide.md             # From USER_GUIDE_RU.md
│   ├── admin-guide.md            # From ADMIN_GUIDE_RU.md
│   └── deployment.md             # From README_DEPLOYMENT.md
├── development/
│   ├── setup.md                  # From DEVELOPER_GUIDE.md
│   ├── architecture.md           # From ARCHITECTURE.md
│   ├── testing.md                # From TESTING_SUMMARY.md
│   └── code-review.md            # From CODE_REVIEW_SUMMARY.md
├── features/
│   ├── nft-markers.md            # Consolidated from 10 NFT files
│   ├── storage-scaling.md        # From storage scaling files
│   └── ar-functionality.md       # AR features documentation
└── archived/
    └── old-files/                # Move obsolete files here
```

## 🗑️ Files to Delete (Duplicates/Obsolete)

### Summary Files (13 → 0)
- ❌ CHANGES_SUMMARY.md
- ❌ CODE_REVIEW_SUMMARY.md  
- ❌ DOCUMENTATION_SUMMARY_RU.md
- ❌ EXECUTIVE_SUMMARY.md
- ❌ IMPLEMENTATION_SUMMARY.md
- ❌ IMPLEMENTATION_SUMMARY_NFT.md
- ❌ NFT_MARKERS_CHECK_SUMMARY.md
- ❌ PATH_FIXES_SUMMARY.md
- ❌ TASK_SUMMARY_STORAGE_SCALING.md
- ❌ TEST_RESULTS_SUMMARY.md
- ❌ VERSION_1.1.0_SUMMARY.md
- ❌ WORK_SUMMARY.md

### NFT Duplicate Files (10 → 1)
- ✅ Keep: NFT_MARKER_IMPROVEMENTS.md (most comprehensive)
- ❌ Delete: NFT_MARKER_API_DOCUMENTATION.md
- ❌ Delete: NFT_MARKER_QUICK_START.md
- ❌ Delete: NFT_GENERATOR_TEST_REPORT.md
- ❌ Delete: NFT_MARKERS_STATUS.md
- ❌ Delete: README_NFT_CHECK.md
- ❌ Delete: ПРОВЕРКА_NFT_ГЕНЕРАТОРА.md
- ❌ Delete: ОТЧЕТ_О_ПРОВЕРКЕ_NFT.md

### README Variants (4 → 1)
- ✅ Keep: README.md (main)
- ❌ Delete: README_RU.md (move content to docs/)
- ❌ Delete: README_DEPLOYMENT.md (move to docs/guides/)
- ❌ Delete: README_NFT_CHECK.md (duplicate)

### Russian Duplicate Files
- ❌ Delete: ИТОГИ_ОБНОВЛЕНИЯ_v1.1.0.md
- ❌ Delete: ГОТОВНОСТЬ_К_ДЕПЛОЮ.md
- ❌ Delete: ДОКУМЕНТАЦИЯ_ПОЛНАЯ_RU.md
- ❌ Delete: ДОКУМЕНТАЦИЯ_СВОДКА_RU.md

### Task/Breakdown Files
- ❌ Delete: TASK_BREAKDOWN.md
- ❌ Delete: NEXT_ACTIONS.md
- ❌ Delete: NEXT_STEPS.md
- ❌ Delete: TODO.md (move content to ROADMAP.md)

### Review/Report Files
- ❌ Delete: CODE_REVIEW_REPORT.md
- ❌ Delete: CODE_REVIEW_README.md
- ❌ Delete: FINAL_TESTING_REPORT.md
- ❌ Delete: FUNCTIONS_REVIEW.md

## 📝 Files to Create

### New Core Files
- CONTRIBUTING.md - Contribution guidelines
- SECURITY.md - Security policy and reporting
- docs/README.md - Documentation index

### Consolidated Content
- docs/api/endpoints.md - From API_DOCUMENTATION.md
- docs/guides/installation.md - From INSTALLATION_GUIDE_RU.md
- docs/features/nft-markers.md - Consolidated from 10 NFT files
- docs/development/testing.md - From TESTING_SUMMARY.md

## 🔄 Migration Steps

### Phase 1: Backup and Preparation
1. ✅ Create backup of current documentation
2. ✅ Update core files (README, CHANGELOG, ROADMAP)
3. 📋 Create docs/ directory structure

### Phase 2: Content Consolidation
1. 📋 Consolidate NFT documentation into single file
2. 📋 Move Russian content to appropriate docs/ files
3. 📋 Extract and organize API documentation
4. 📋 Create guides from existing files

### Phase 3: Cleanup
1. 📋 Move obsolete files to archived/
2. 📋 Delete duplicate files
3. 📋 Update all internal links
4. 📋 Verify documentation completeness

### Phase 4: Finalization
1. 📋 Create docs/README.md index
2. 📋 Add CONTRIBUTING.md
3. 📋 Update all references
4. 📋 Final link validation

## 📊 Expected Result

- **Before:** 67 documentation files (many duplicates)
- **After:** ~15 well-organized files
- **Reduction:** ~78% fewer files
- **Organization:** Clear hierarchy and structure
- **Maintenance:** Much easier to maintain and update

## ⚠️ Important Notes

- All content will be preserved during reorganization
- No information will be lost, only reorganized
- All internal links will be updated
- Archived files will be kept temporarily for reference
- Russian documentation will be properly integrated