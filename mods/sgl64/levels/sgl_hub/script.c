#include <ultra64.h>
#include "sm64.h"
#include "behavior_data.h"
#include "model_ids.h"
#include "seq_ids.h"
#include "dialog_ids.h"
#include "segment_symbols.h"
#include "level_commands.h"

#include "game/level_update.h"

#include "levels/scripts.h"

#include "make_const_nonconst.h"
#include "levels/sgl_hub/header.h"

/* Fast64 begin persistent block [scripts] */
/* Fast64 end persistent block [scripts] */

const LevelScript level_sgl_hub_entry[] = {
	INIT_LEVEL(),
	LOAD_MIO0(0x07, _sgl_hub_segment_7SegmentRomStart, _sgl_hub_segment_7SegmentRomEnd),
	LOAD_MIO0(0x0A, _water_skybox_mio0SegmentRomStart, _water_skybox_mio0SegmentRomEnd),
	ALLOC_LEVEL_POOL(),
	MARIO(MODEL_MARIO, 0x00000001, bhvMario),
	/* Fast64 begin persistent block [level commands] */
	/* Fast64 end persistent block [level commands] */

	AREA(1, sgl_hub_area_1),
		WARP_NODE(0x0A, LEVEL_CASTLE, 0x01, 0x0A, WARP_NO_CHECKPOINT),
		WARP_NODE(0xF0, LEVEL_CASTLE, 0x01, 0x32, WARP_NO_CHECKPOINT),
		WARP_NODE(0xF1, LEVEL_CASTLE, 0x01, 0x64, WARP_NO_CHECKPOINT),
		OBJECT(MODEL_NONE, 7180, 0, 150, 0, 0, 0, 0x002B0000, bhvPoleGrabbing),
		OBJECT(MODEL_NONE, 9460, 0, 150, 0, 0, 0, 0x002B0000, bhvPoleGrabbing),
		OBJECT(MODEL_NONE, 5900, 0, 940, 0, 0, 0, 0x002B0000, bhvPoleGrabbing),
		OBJECT(MODEL_NONE, 10700, 0, 940, 0, 0, 0, 0x002B0000, bhvPoleGrabbing),
		OBJECT(MODEL_NONE, 4700, 0, 940, 0, 0, 0, 0x002B0000, bhvPoleGrabbing),
		OBJECT(MODEL_NONE, 11900, 0, 940, 0, 0, 0, 0x002B0000, bhvPoleGrabbing),
		OBJECT(MODEL_NONE, 7450, 0, 3110, 0, 0, 0, 0x002B0000, bhvPoleGrabbing),
		OBJECT(MODEL_NONE, 9230, 0, 3110, 0, 0, 0, 0x002B0000, bhvPoleGrabbing),
		OBJECT(MODEL_NONE, -300, 0, 8600, 0, 0, 0, 0x002B0000, bhvPoleGrabbing),
		OBJECT(MODEL_NONE, -300, 0, 11200, 0, 0, 0, 0x002B0000, bhvPoleGrabbing),
		OBJECT(MODEL_NONE, -2700, 0, 11400, 0, 0, 0, 0x002B0000, bhvPoleGrabbing),
		OBJECT(MODEL_NONE, -5700, 0, 11600, 0, 0, 0, 0x002B0000, bhvPoleGrabbing),
		OBJECT(MODEL_NONE, -7500, 0, 12150, 0, 0, 0, 0x002B0000, bhvPoleGrabbing),
		OBJECT(MODEL_NONE, 350, 0, 5800, 0, 0, 0, 0x002B0000, bhvPoleGrabbing),
		MARIO_POS(0x01, -10, 8320, 100, -4440),
		OBJECT(MODEL_WOODEN_SIGNPOST, 4666, 0, 9168, 0, -180, 0, SGL_HUB_SIGN_CENTURY_TOWER, bhvMessagePanel),
		OBJECT(MODEL_WOODEN_SIGNPOST, 3693, 0, 10157, 0, -90, 0, SGL_HUB_SIGN_FINAL_EXAM, bhvMessagePanel),
		OBJECT(MODEL_WOODEN_SIGNPOST, 8651, 0, -15743, 0, 0, 0, SGL_HUB_SIGN_LIBRARY_WEST, bhvMessagePanel),
		OBJECT(MODEL_WOODEN_SIGNPOST, -1670, 90, 16250, 0, -180, 0, SGL_HUB_SIGN_MARSTON, bhvMessagePanel),
		OBJECT(MODEL_WOODEN_SIGNPOST, -10668, 0, 6515, 0, 90, 0, SGL_HUB_SIGN_NEWELL_HALL, bhvMessagePanel),
		OBJECT(MODEL_WOODEN_SIGNPOST, 16895, 0, -14421, 0, -90, 0, SGL_HUB_SIGN_SMATHERS, bhvMessagePanel),
		OBJECT(MODEL_WOODEN_SIGNPOST, -14598, 0, 18356, 0, 36, 0, SGL_HUB_SIGN_THE_HUB, bhvMessagePanel),
		OBJECT(MODEL_WOODEN_SIGNPOST, 8098, 0, 3208, 0, 178, 0, SGL_HUB_SIGN_UNIVERSITY_AUDITORIUM, bhvMessagePanel),
		OBJECT(MODEL_WOODEN_SIGNPOST, 8364, 0, -3942, 0, -175, 0, SGL_HUB_SIGN_WELCOME, bhvMessagePanel),
		OBJECT(MODEL_NONE, 8320, 100, -4440, 0, -10, 0, 0x000A0000, bhvSpinAirborneWarp),
		OBJECT(MODEL_NONE, 4959, 0, -2675, 0, 0, 0, 0x00000000, bhvTree),
		OBJECT(MODEL_NONE, 4878, 0, -5166, 0, 0, 0, 0x00000000, bhvTree),
		OBJECT(MODEL_NONE, 4785, 0, -7620, 0, 0, 0, 0x00000000, bhvTree),
		OBJECT(MODEL_NONE, 4899, 0, -7011, 0, 0, 0, 0x00000000, bhvTree),
		OBJECT(MODEL_NONE, 4709, 0, -8460, 0, 0, 0, 0x00000000, bhvTree),
		OBJECT(MODEL_NONE, 5019, 0, -6049, 0, 0, 0, 0x00000000, bhvTree),
		OBJECT(MODEL_NONE, 5623, 0, -4154, 0, 0, 0, 0x00000000, bhvTree),
		OBJECT(MODEL_NONE, 9759, 0, -3885, 0, 0, 0, 0x00000000, bhvTree),
		OBJECT(MODEL_NONE, 14733, 0, -3864, 0, 0, 0, 0x00000000, bhvTree),
		OBJECT(MODEL_NONE, 14651, 0, -2085, 0, 0, 0, 0x00000000, bhvTree),
		OBJECT(MODEL_NONE, 15367, 0, -3647, 0, 0, 0, 0x00000000, bhvTree),
		OBJECT(MODEL_NONE, 13057, 0, -5346, 0, 0, 0, 0x00000000, bhvTree),
		OBJECT(MODEL_NONE, 9681, 0, -2810, 0, 0, 0, 0x00000000, bhvTree),
		OBJECT(MODEL_NONE, 15387, 0, -4808, 0, 0, 0, 0x00000000, bhvTree),
		OBJECT(MODEL_NONE, 14628, 0, -3269, 0, 0, 0, 0x00000000, bhvTree),
		OBJECT(MODEL_NONE, 10446, 0, -2129, 0, 0, 0, 0x00000000, bhvTree),
		OBJECT(MODEL_NONE, 14788, 0, -2832, 0, 0, 0, 0x00000000, bhvTree),
		OBJECT(MODEL_NONE, 10681, 0, -5045, 0, 0, 0, 0x00000000, bhvTree),
		OBJECT(MODEL_NONE, 9693, 0, -6353, 0, 0, 0, 0x00000000, bhvTree),
		OBJECT(MODEL_NONE, 13786, 0, -3517, 0, 0, 0, 0x00000000, bhvTree),
		OBJECT(MODEL_NONE, 12412, 0, -6082, 0, 0, 0, 0x00000000, bhvTree),
		OBJECT(MODEL_NONE, 9787, 0, -4919, 0, 0, 0, 0x00000000, bhvTree),
		OBJECT(MODEL_NONE, 11732, 0, -3745, 0, 0, 0, 0x00000000, bhvTree),
		OBJECT(MODEL_NONE, 12533, 0, -2974, 0, 0, 0, 0x00000000, bhvTree),
		OBJECT(MODEL_NONE, 13815, 0, -5348, 0, 0, 0, 0x00000000, bhvTree),
		OBJECT(MODEL_NONE, 13801, 0, -9099, 0, 0, 0, 0x00000000, bhvTree),
		OBJECT(MODEL_NONE, 13746, 0, -8220, 0, 0, 0, 0x00000000, bhvTree),
		OBJECT(MODEL_NONE, 13745, 0, -6927, 0, 0, 0, 0x00000000, bhvTree),
		TERRAIN(sgl_hub_area_1_collision),
		MACRO_OBJECTS(sgl_hub_area_1_macro_objs),
		SET_BACKGROUND_MUSIC(0x00, SEQ_LEVEL_GRASS),
		TERRAIN_TYPE(TERRAIN_GRASS),
		/* Fast64 begin persistent block [area commands] */
		/* Fast64 end persistent block [area commands] */
	END_AREA(),
	FREE_LEVEL_POOL(),
	MARIO_POS(0x01, -10, 8320, 100, -4440),
	CALL(0, lvl_init_or_update),
	CALL_LOOP(1, lvl_init_or_update),
	CLEAR_LEVEL(),
	SLEEP_BEFORE_EXIT(1),
	EXIT(),
};