from typing import Union
from fastapi import APIRouter, Query, Request

from pydantic.types import Json
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from sqlalchemy import delete, insert, select, update, text

from .schemas import RaResponseModel

class ReactAdmin:
    def __init__(self, 
        table: any,
        *,
        router: APIRouter,
        session: async_sessionmaker[AsyncSession],
        prefix: str = '/ra',
        deleted_field: str = None,
        exclude_deleted: str = True,
        include_in_schema: bool = False,
    ) -> None:
        '''
        Initializes a ReactAdmin instance.

        Args:
            table: The SQLAlchemy model representing the database table.
            router: The APIRouter instance to mount the routes.
            session: The async_sessionmaker[AsyncSession] for the database session.
            prefix: The URL prefix for the react admin routes.
            deleted_field: The name of the field of the table for mark deleted fields (like is_deleted) (optional).
            exclude_deleted: Whether to exclude deleted records (optional).
            include_in_schema: Whether to include the routes in the generated schema (optional).
        '''
        
        self.table = table
        self.user_router = router
        self.Session = session
        self.deleted_filed = deleted_field
        self.exclude_deleted = exclude_deleted

        self._router = APIRouter(
            prefix=prefix, 
            tags=['React Admin routers'], 
            include_in_schema=include_in_schema
        )
    
    def mount(self):
        '''
        Mounts the routes to the user_router.
        '''
        
        self._router.add_api_route('/getList', self._get_list, response_model=RaResponseModel, methods=['POST'])
        self._router.add_api_route('/getOne/{id}', self._get_one, response_model=RaResponseModel, methods=['POST'])
        self._router.add_api_route('/getMany/{id}', self._get_many, response_model=RaResponseModel, methods=['POST'])
        self._router.add_api_route('/create', self._create, response_model=RaResponseModel, methods=['POST'])
        self._router.add_api_route('/update/{id}', self._update, response_model=RaResponseModel, methods=['POST'])
        self._router.add_api_route('/updateMany', self._update_many, response_model=RaResponseModel, methods=['POST'])
        self._router.add_api_route('/delete/{id}', self._delete, response_model=RaResponseModel, methods=['POST'])
        self._router.add_api_route('/deleteMany', self._delete_many, response_model=RaResponseModel, methods=['POST'])

        self.user_router.include_router(self._router)

    async def _get_list(self, 
        sort: Json = Query(), 
        filter: Json = Query(), 
        range_: Json = Query()
    ):  
        if self.deleted_filed and self.exclude_deleted:
            filter[self.deleted_filed] = False

        async with self.Session() as session:
            result = (await session.execute(
                select(self.table).filter_by(
                    **filter
                ).order_by(
                    text(f"{sort[0]} {sort[1]}")
                )
            )).scalars().all()

            return RaResponseModel(
                data=result[range_[0]:range_[1] + 1],
                total=len(result)
            )
    
    async def _get_one(self, id: Union[int, str]):
        async with self.Session() as session:
            result = await session.get(self.table, id)
            return RaResponseModel(data=result)
    
    async def _get_many(self, filter: Json = Query()):
        if self.deleted_filed and self.exclude_deleted:
            filter[self.deleted_filed] = False

        async with self.Session() as session:
            result = await session.execute(
                select(self.table).where(
                    self.table.id.in_(filter['id'])
                ).filter_by(
                    **filter
                )
            )
        
            return RaResponseModel(data=result)

    async def _create(self, request: Request):
        async with self.Session() as session:
            result = await session.execute(
                insert(self.table).values(
                    **(await request.json())
                ).returning(self.table)
            )

            await session.commit()
            return RaResponseModel(data=result.scalar())

    async def _update(self, id: Union[int, str], request: Request):
        async with self.Session() as session:
            result =  await session.execute(
                update(self.table).values(
                    **(await request.json())
                ).where(self.table.id == id).returning(self.table)
            )

            await session.commit()
            return RaResponseModel(data=result.scalar())

    async def _update_many(self, request: Request, filter: Json = Query()):
        async with self.Session() as session:
            await session.execute(
                update(self.table).values(
                    **(await request.json())
                ).where(self.table.id.in_(filter['id']))
            )

            await session.commit()
            return RaResponseModel(data=filter['id'])
        
    async def _delete(self, id: Union[int, str]):
        async with self.Session() as session:
            if not self.deleted_filed: 
                req = delete(self.table).where(
                    self.table.id == id
                ).returning(self.table)

            else: 
                req = update(self.table).where(
                    self.table.id == id
                ).values(
                    {self.deleted_filed: True}
                ).returning(self.table)

            result = await session.execute(req)

            await session.commit()
            return RaResponseModel(data=result.scalar())   

    async def _delete_many(self, filter: Json = Query()):
        async with self.Session() as session:
            if not self.deleted_filed: 
                req = delete(self.table).where(
                    self.table.id.in_(filter['id'])
                ).returning(self.table)

            else: 
                req = update(self.table).where(
                    self.table.id.in_(filter['id'])
                ).values(
                    {self.deleted_filed: True}
                ).returning(self.table)

            await session.execute(req)

            await session.commit()
            return RaResponseModel(data=filter['id'])
