import pickle
from pathlib import Path

from findata.call_findata_api import create_description, fetch_findata

BASE_DIR = Path(__file__).resolve().parent.parent
data_path = BASE_DIR / "findata" / "data"

data = create_description(fetch_findata("fixed_deposit"))
data.extend(create_description(fetch_findata("installment_deposit")))
data.extend(create_description(fetch_findata("jeonse_loan")))

# 파일로 저장
with open(data_path / "findata_all.pkl", "wb") as f:
    pickle.dump(data, f)

# 파일 불러오기
# with open(data_path / "findata_all.pkl", "rb") as f:
#     loaded_data = pickle.load(f)

# print(loaded_data)
