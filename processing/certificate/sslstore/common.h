#ifndef __COMMON_H__
#define __COMMON_H__

namespace table {

enum AddonTypes {
	atUnknown		= 0
	, atBoolean		= 1
	, atInteger		= 2
	, atEnum		= 3
};

enum BillTypes {
	btUnknown		= 0
	, btNone		= 1
	, btOrdered		= 2
	, btStat		= 3
	, btCompound	= 4  //выбирается клиентом из нескольких
	, btManual		= 10 //вручную созданное для услуги дополнение
};

enum TaskStatus {
	tsOpened	= 0
	, tsInWork	= 1
	, tsClosed	= 2
};

}

#endif