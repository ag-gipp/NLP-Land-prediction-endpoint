"""This module implements the endpoint logic for models."""
from importlib import import_module
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel

from cs_insights_prediction_endpoint import __version__
from cs_insights_prediction_endpoint.models.generic_model import (
    GenericInputModel,
    GenericOutputModel,
)
from cs_insights_prediction_endpoint.utils.remote_storage_controller import (
    RemoteStorageController,
    get_remote_storage_controller,
)

# from cs_insights_prediction_endpoint.models.lda_model import LDAModel
from cs_insights_prediction_endpoint.utils.settings import Settings, get_settings
from cs_insights_prediction_endpoint.utils.storage_controller import (
    StorageController,
    get_storage_controller,
)

router: APIRouter = APIRouter()


class StorageControllerListReponse(BaseModel):
    """Response model for both
        - GET /
        - GET /implemented
    which returns a list of models
    """

    models: List[str]
    # error: str


class ModelSpecificFunctionCallResponse(BaseModel):
    """Response model for model specific function calls"""

    functionCalls: List[str]


class ModelCreationResponse(BaseModel):
    """Response Model for the successfull creation of a model"""

    modelID: str


class ModelDeletionResponse(BaseModel):
    """Response Model for the successfull deletion of a model"""

    modelID: str


# TODO-AT TN: I just copied the ModelCreationRequest,
#         since this class was used but i could not find it
#         please change
class ModelDeletionRequest(BaseModel):
    """Response model for creating a Model
    This contains the modelType (e.g., lda) and the model specification
    which should be parsable to the modelTypes pydentic schema.
    """

    modelID: str


# TODO-AT TN: I just copied the ModelCreationRequest,
#         since this class was used but i could not find it
#         please change
class ModelFunctionRequest(BaseModel):
    """Response model for creating a Model
    This contains the modelType (e.g., lda) and the model specification
    which should be parsable to the modelTypes pydentic schema.
    """

    modelID: str


# TODO-AT TN: I just copied the ModelCreationRequest,
#         since this class was used but i could not find it
#         please change
class ModelUpdateRequest(BaseModel):
    """Response model for creating a Model
    This contains the modelType (e.g., lda) and the model specification
    which should be parsable to the modelTypes pydentic schema.
    """

    modelID: str
    modelSpecification: dict


class ModelCreationRequest(BaseModel):
    """Response model for creating a Model
    This contains the modelType (e.g., lda) and the model specification
    which should be parsable to the modelTypes pydentic schema.
    """

    # XXX-TN I puropsefully chose modelSpecification to be a dict since
    #          using the generic model, would incur the loss of pydantics strengths
    modelType: str
    # XXX-TN For the docker ochestration it will be helpfull to also have an input for
    #        the location of Model initialization (local, local[dockerfile], remote)
    modelSpecification: dict


@router.get(
    "/implemented",
    response_description="Lists all currently available(implemented) models",
    response_model=StorageControllerListReponse,
    status_code=status.HTTP_200_OK,
)
def list_all_implemented_models(
    settings: Settings = Depends(get_settings),
    rsc: RemoteStorageController = Depends(get_remote_storage_controller),
) -> StorageControllerListReponse:
    """Endpoint for getting a list of all implemented models"""
    models = []
    for implemented_models in settings.IMPLEMENTED_MODELS:
        for implemented_model in implemented_models.keys():
            models.append(implemented_model)
    return StorageControllerListReponse(models=models)


@router.get(
    "/{current_modelID}",
    response_description="Lists all function calls of the current model",
    response_model=ModelSpecificFunctionCallResponse,
    status_code=status.HTTP_200_OK,
)
def list_all_function_calls(
    current_modelID: str, sc: StorageController = Depends(get_storage_controller)
) -> BaseModel:
    """Endpoint for getting a list of all implemented function calls"""
    # validate id
    currentModel = sc.getModel(current_modelID)
    if currentModel is None:
        # error not found
        raise HTTPException(status_code=404, detail="Model not found")

    # get fun calls
    cMFCalls = currentModel.getFunctionCalls()  # current model functioncalls list
    return ModelSpecificFunctionCallResponse(functionCalls=cMFCalls)


@router.delete(
    "/{current_modelID}",
    response_description="Delete the current model",
    response_model=ModelDeletionResponse,
    status_code=status.HTTP_200_OK,
)
def deleteModel(
    current_modelID: str, sc: StorageController = Depends(get_storage_controller)
) -> ModelDeletionResponse:
    """Endpoint for deleting a model"""
    # validate id
    currentModel = sc.getModel(current_modelID)
    if currentModel is None:
        # error not found
        raise HTTPException(status_code=404, detail="Model not implemented")

    # delete it
    sc.delModel(currentModel.getId())
    return ModelDeletionResponse(modelID=current_modelID)


# TODO-AT I could not get this to work/don't understand what needs to be done
#         and i think we should not be calling other endpoint functions
# XXX-AT Some do it like that, but with "FastAPI" and some use just "get" for it.
#        Other question would be, if we actually need this, if we have delete and put.
#        Is there a reason, why we use "API-Router" and not "FastAPI"?
# @router.patch(
#     "/{current_modelID}",
#     response_description="Update the current model",
#     response_model=ModelCreationResponse,
#     status_code=status.HTTP_201_CREATED,
# )
# def updateModel(
#     modelCreationRequest: ModelCreationRequest, response: Response, current_modelID: str
# ) -> BaseModel:
#     """Endpoint for updating a model"""
#     # validate id
#     currentModel = storage.getModel(current_modelID)
#     if currentModel is None:
#         # error not found
#         raise HTTPException(status_code=404, detail="Model not implemented")
#
#     # create new, delete old
#     newID = create_model(modelCreationRequest, response)
#     storage.delModel(currentModel.getId())
#     return ModelCreationResponse(modelID=newID)


@router.get(
    "/",
    response_description="Lists all currently created models",
    response_model=StorageControllerListReponse,
    status_code=status.HTTP_200_OK,
)
def list_all_created_models(
    settings: Settings = Depends(get_settings),
    sc: StorageController = Depends(get_storage_controller),
) -> StorageControllerListReponse:
    """Endpoint for getting a list of all created models"""
    all_models = list([str(i) for i in sc.getAllModels()])
    return StorageControllerListReponse(models=all_models)


@router.post(
    "/",
    response_description="Creates a model",
    response_model=ModelCreationResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_model(
    modelCreationRequest: ModelCreationRequest,
    response: Response,
    settings: Settings = Depends(get_settings),
    sc: StorageController = Depends(get_storage_controller),
) -> ModelCreationResponse:
    """Endpoint for creating a model

    Arguments:
        modelCreationRequest (ModelCreationRequest): A ModelCreationRequest used for the creation
                                                 of the actual model

    Returns:
        dict: Either an error or the created model id
    """
    model = None
    # TODO-TN We need to have a list with all implemented models
    for implemented_models in settings.IMPLEMENTED_MODELS:
        if modelCreationRequest.modelType in implemented_models:
            model_specs = implemented_models[modelCreationRequest.modelType]
            model_module = import_module(model_specs[0])  # TODO Use proper model
            model_class = model_specs[1]
            model = getattr(model_module, model_class)(
                type=modelCreationRequest.modelType, **(modelCreationRequest.modelSpecification)
            )
    if model is None:
        raise HTTPException(status_code=404, detail="Model not implemented")
    sc.addModel(model)
    response.headers["location"] = f"/api/v{__version__.split('.')[0]}/models/{model.id}"

    return ModelCreationResponse(modelID=model.id)


@router.post(
    "/{current_modelID}",
    response_description="Runs a function",
    response_model=GenericOutputModel,
    status_code=status.HTTP_200_OK,
)
def getInformation(
    current_modelID: str,
    genericInput: GenericInputModel,
    sc: StorageController = Depends(get_storage_controller),
) -> BaseModel:
    """Gets info out of post data"""
    return run_function(current_modelID, genericInput.functionCall, genericInput.inputData, sc)


def run_function(
    current_modelID: str, req_function: str, data_input: Dict[Any, Any], sc: StorageController
) -> BaseModel:
    """Runs a given function of a given model"""
    # Validate id
    currentModel = sc.getModel(current_modelID)
    if currentModel is None:
        # error not found
        raise HTTPException(status_code=404, detail="Model not found")

    # Check if the function is actually availabe in the requested model
    # Return an HTTPException if not; Execute the function and return Dict otherwise
    try:
        myFun = getattr(currentModel, req_function)
    except AttributeError:
        raise HTTPException(status_code=404, detail="Function not implemented")

    # Run function and parse output dict into actual response model
    output = myFun(**data_input)
    # XXX-TN we have to ensure that we return a dict on a function call
    #        i dont know if the following is the best way to achive this
    if not type(output) is dict:
        # raise HTTPException(status_code=500, detail="Model did not return a valid response")
        output = {req_function: str(output)}  # TODO-TN this is relly hacky
    outModelResp = GenericOutputModel(outputData=output)

    return outModelResp