from enum import Enum
import datetime
import uuid


class ParkingSpaceType(Enum):
    REGULAR = "REGULAR"
    LARGE = "LARGE"
    HANDICAPPED = "HANDICAPPED"
    ELECTRIC = "ELECTRIC"


class VehicleType(Enum):
    CAR = "CAR"
    SUV = "SUV"
    TRUCK = "TRUCK"
    ELECTRIC_CAR = "ELECTRIC_CAR"


class Vehicle:
    def __init__(self, vehicle_id: str, vehicle_type: VehicleType):
        self.vehicle_id = vehicle_id
        self.vehicle_type = vehicle_type


class ParkingSpace:
    def __init__(self, space_id: str, space_type: ParkingSpaceType):
        self.space_id = space_id
        self.space_type = space_type
        self.is_occupied = False
        self.vehicle = None
        self.entry_time = None

    def occupy(self, vehicle: Vehicle, entry_time: datetime.datetime):
        """占用停车位"""
        self.is_occupied = True
        self.vehicle = vehicle
        self.entry_time = entry_time

    def free(self) -> tuple:
        """释放停车位，返回车辆和进入时间"""
        self.is_occupied = False
        vehicle = self.vehicle
        entry_time = self.entry_time
        self.vehicle = None
        self.entry_time = None
        return vehicle, entry_time


class Floor:
    def __init__(self, floor_number: int, space_capacities: dict):
        """
        初始化楼层
        :param floor_number: 楼层号
        :param space_capacities: 车位类型及数量字典，如 {ParkingSpaceType.REGULAR: 50}
        """
        self.floor_number = floor_number
        self.parking_spaces = []
        self._create_spaces(space_capacities)

    def _create_spaces(self, space_capacities: dict):
        """创建楼层的所有停车位"""
        for space_type, count in space_capacities.items():
            for i in range(count):
                space_id = f"{self.floor_number}-{space_type.value}-{i+1}"
                self.parking_spaces.append(ParkingSpace(space_id, space_type))

    def get_available_spaces(self, space_type: ParkingSpaceType = None) -> list:
        """获取可用停车位"""
        if space_type:
            return [space for space in self.parking_spaces if not space.is_occupied and space.space_type == space_type]
        return [space for space in self.parking_spaces if not space.is_occupied]

    def find_available_space(self, vehicle_type: VehicleType) -> ParkingSpace:
        """根据车辆类型查找可用停车位"""
        required_space_type = self._get_required_space_type(vehicle_type)
        available_spaces = self.get_available_spaces(required_space_type)
        return available_spaces[0] if available_spaces else None

    def _get_required_space_type(self, vehicle_type: VehicleType) -> ParkingSpaceType:
        """映射车辆类型到所需的车位类型"""
        mapping = {
            VehicleType.CAR: ParkingSpaceType.REGULAR,
            VehicleType.SUV: ParkingSpaceType.LARGE,
            VehicleType.TRUCK: ParkingSpaceType.LARGE,
            VehicleType.ELECTRIC_CAR: ParkingSpaceType.ELECTRIC
        }
        return mapping.get(vehicle_type, ParkingSpaceType.REGULAR)


class PricingManager:
    def __init__(self, base_rates: dict):
        """
        初始化定价管理器
        :param base_rates: 基础费率字典，如 {(ParkingSpaceType.REGULAR, VehicleType.CAR): 5}
        """
        self.base_rates = base_rates

    def calculate_fee(self, space_type: ParkingSpaceType, vehicle_type: VehicleType, duration_hours: float) -> float:
        """根据车位类型、车辆类型和时长计算费用"""
        rate = self.base_rates.get((space_type, vehicle_type), 0)
        return round(rate * duration_hours, 2)


class Transaction:
    def __init__(self, transaction_id: str, space: ParkingSpace, vehicle: Vehicle, entry_time: datetime.datetime):
        self.transaction_id = transaction_id
        self.space = space
        self.vehicle = vehicle
        self.entry_time = entry_time
        self.exit_time = None
        self.duration_hours = 0
        self.fee = 0

    def complete(self, exit_time: datetime.datetime, fee: float):
        """完成交易"""
        self.exit_time = exit_time
        self.duration_hours = round((exit_time - self.entry_time).total_seconds() / 3600, 2)
        self.fee = fee

    def generate_receipt(self) -> str:
        """生成收据"""
        receipt = f"""
        ---------------- PARKING RECEIPT ----------------
        Transaction ID: {self.transaction_id}
        Vehicle ID: {self.vehicle.vehicle_id}
        Vehicle Type: {self.vehicle.vehicle_type.value}
        Parking Space: {self.space.space_id}
        Entry Time: {self.entry_time.strftime("%Y-%m-%d %H:%M:%S")}
        Exit Time: {self.exit_time.strftime("%Y-%m-%d %H:%M:%S")}
        Duration: {self.duration_hours} hours
        Total Fee: ${self.fee}
        --------------------------------------------------
        """
        return receipt


class ParkingLot:
    def __init__(self, floors: list, pricing_manager: PricingManager):
        self.floors = floors
        self.pricing_manager = pricing_manager
        self.transactions = {}  # 存储所有交易记录
        self.current_transactions = {}  # 存储当前正在进行的交易 (space_id -> transaction_id)

    def vehicle_entry(self, vehicle: Vehicle) -> dict:
        """车辆进入停车场"""
        # 查找可用停车位
        for floor in self.floors:
            space = floor.find_available_space(vehicle.vehicle_type)
            if space:
                entry_time = datetime.datetime.now()
                space.occupy(vehicle, entry_time)
                
                # 创建交易记录
                transaction_id = str(uuid.uuid4())
                transaction = Transaction(transaction_id, space, vehicle, entry_time)
                self.transactions[transaction_id] = transaction
                self.current_transactions[space.space_id] = transaction_id
                
                return {
                    "success": True,
                    "floor": floor.floor_number,
                    "space_id": space.space_id,
                    "entry_time": entry_time,
                    "transaction_id": transaction_id,
                    "message": "车辆已成功进入停车场"
                }
        
        return {
            "success": False,
            "message": "停车场已满，无可用停车位"
        }

    def vehicle_exit(self, transaction_id: str) -> str:
        """车辆离开停车场"""
        if transaction_id not in self.transactions:
            return "无效的交易ID"
            
        transaction = self.transactions[transaction_id]
        if transaction.exit_time:
            return "该车辆已离开停车场"
            
        # 释放停车位
        space = transaction.space
        vehicle, entry_time = space.free()
        
        # 计算费用
        exit_time = datetime.datetime.now()
        duration_hours = round((exit_time - entry_time).total_seconds() / 3600, 2)
        fee = self.pricing_manager.calculate_fee(space.space_type, vehicle.vehicle_type, duration_hours)
        
        # 完成交易
        transaction.complete(exit_time, fee)
        
        # 从当前交易中移除
        if space.space_id in self.current_transactions:
            del self.current_transactions[space.space_id]
        
        # 生成收据
        return transaction.generate_receipt()

    def get_available_spaces_info(self) -> list:
        """获取停车场可用车位信息"""
        available_info = []
        for floor in self.floors:
            floor_info = {
                "floor": floor.floor_number,
                "spaces": {}
            }
            for space_type in ParkingSpaceType:
                count = len(floor.get_available_spaces(space_type))
                floor_info["spaces"][space_type.value] = count
            available_info.append(floor_info)
        return available_info


class StatisticsManager:
    def __init__(self, parking_lot: ParkingLot):
        self.parking_lot = parking_lot
        self.daily_stats = {}  # 存储每日统计数据

    def generate_daily_stats(self, date: datetime.datetime = None) -> dict:
        """生成每日统计数据"""
        if not date:
            date = datetime.datetime.now()
        
        date_str = date.strftime("%Y-%m-%d")
        
        # 如果已存在当天统计数据，直接返回
        if date_str in self.daily_stats:
            return self.daily_stats[date_str]
        
        # 筛选当天的交易记录
        daily_transactions = [
            transaction for transaction in self.parking_lot.transactions.values()
            if transaction.entry_time.strftime("%Y-%m-%d") == date_str
        ]
        
        # 计算统计数据
        total_vehicles = len(daily_transactions)
        total_revenue = sum(transaction.fee for transaction in daily_transactions)
        
        # 计算车位使用率
        total_spaces = sum(len(floor.parking_spaces) for floor in self.parking_lot.floors)
        total_occupied_hours = sum(transaction.duration_hours for transaction in daily_transactions)
        occupancy_rate = round((total_occupied_hours / (total_spaces * 24)) * 100, 2) if total_spaces > 0 else 0
        
        # 车辆类型分布
        vehicle_type_distribution = {}
        for transaction in daily_transactions:
            vt = transaction.vehicle.vehicle_type.value
            vehicle_type_distribution[vt] = vehicle_type_distribution.get(vt, 0) + 1
        
        # 存储统计数据
        stats = {
            "date": date_str,
            "total_vehicles": total_vehicles,
            "total_revenue": total_revenue,
            "occupancy_rate": occupancy_rate,
            "vehicle_type_distribution": vehicle_type_distribution,
            "total_spaces": total_spaces
        }
        
        self.daily_stats[date_str] = stats
        return stats


# 示例用法
if __name__ == "__main__":
    # 初始化定价
    base_rates = {
        (ParkingSpaceType.REGULAR, VehicleType.CAR): 5,
        (ParkingSpaceType.LARGE, VehicleType.SUV): 7,
        (ParkingSpaceType.LARGE, VehicleType.TRUCK): 10,
        (ParkingSpaceType.ELECTRIC, VehicleType.ELECTRIC_CAR): 6
    }
    pricing_manager = PricingManager(base_rates)
    
    # 初始化楼层
    floor1 = Floor(1, {
        ParkingSpaceType.REGULAR: 2,
        ParkingSpaceType.LARGE: 1,
        ParkingSpaceType.ELECTRIC: 1
    })
    
    floor2 = Floor(2, {
        ParkingSpaceType.REGULAR: 3,
        ParkingSpaceType.LARGE: 2
    })
    
    floors = [floor1, floor2]
    
    # 初始化停车场
    parking_lot = ParkingLot(floors, pricing_manager)
    
    # 初始化统计管理器
    stats_manager = StatisticsManager(parking_lot)
    
    print("=== 停车管理系统示例 ===")
    
    # 车辆进入
    car1 = Vehicle("ABC123", VehicleType.CAR)
    entry_result1 = parking_lot.vehicle_entry(car1)
    print(f"车辆1进入: {entry_result1['message']}")
    if entry_result1["success"]:
        print(f"分配车位: 楼层 {entry_result1['floor']}, 车位 {entry_result1['space_id']}")
        print(f"交易ID: {entry_result1['transaction_id']}")
    
    print()
    
    # 车辆进入
    suv1 = Vehicle("DEF456", VehicleType.SUV)
    entry_result2 = parking_lot.vehicle_entry(suv1)
    print(f"车辆2进入: {entry_result2['message']}")
    if entry_result2["success"]:
        print(f"分配车位: 楼层 {entry_result2['floor']}, 车位 {entry_result2['space_id']}")
        print(f"交易ID: {entry_result2['transaction_id']}")
    
    print()
    
    # 查看可用车位
    available_spaces = parking_lot.get_available_spaces_info()
    print("当前可用车位信息:")
    for floor_info in available_spaces:
        print(f"楼层 {floor_info['floor']}: {floor_info['spaces']}")
    
    print()
    
    # 车辆离开
    if entry_result1["success"]:
        receipt1 = parking_lot.vehicle_exit(entry_result1["transaction_id"])
        print("车辆1离开收据:")
        print(receipt1)
    
    print()
    
    # 查看可用车位
    available_spaces = parking_lot.get_available_spaces_info()
    print("当前可用车位信息:")
    for floor_info in available_spaces:
        print(f"楼层 {floor_info['floor']}: {floor_info['spaces']}")
    
    print()
    
    # 生成今日统计
    today_stats = stats_manager.generate_daily_stats()
    print("今日统计数据:")
    print(f"日期: {today_stats['date']}")
    print(f"总车辆数: {today_stats['total_vehicles']}")
    print(f"总收入: ${today_stats['total_revenue']}")
    print(f"车位使用率: {today_stats['occupancy_rate']}%")
    print(f"车辆类型分布: {today_stats['vehicle_type_distribution']}")
    print(f"总车位数: {today_stats['total_spaces']}")