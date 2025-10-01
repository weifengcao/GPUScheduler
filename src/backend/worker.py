import asyncio
import boto3
from celery import Celery
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta

from src.backend.core.config import settings
from src.backend.core.database import AsyncSessionLocal
from src.backend.models.gpu import GPU, GpuStatus

celery_app = Celery(
    "worker",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

celery_app.conf.update(
    task_track_started=True,
)

@celery_app.task(bind=True)
def provision_gpu(self, allocation_request: dict):
    """
    A Celery task to provision a new GPU on AWS.
    """
    async def _provision():
        print(f"Received GPU provisioning task with data: {allocation_request}")
        db: AsyncSession = AsyncSessionLocal()

        # Create a new GPU record in the database
        new_gpu = GPU(
            organization_id=allocation_request["organization_id"],
            user_id=allocation_request["user_id"],
            status=GpuStatus.PROVISIONING,
            lease_expires_at=datetime.utcnow() + timedelta(hours=1) # Default 1 hour lease
        )
        db.add(new_gpu)
        await db.commit()
        await db.refresh(new_gpu)
        print(f"Created new GPU record with ID: {new_gpu.id}")

        try:
            ec2 = boto3.resource("ec2", region_name=settings.AWS_REGION)

            instance = ec2.create_instances(
                ImageId=settings.AWS_AMI_ID,
                InstanceType=settings.AWS_INSTANCE_TYPE,
                MinCount=1,
                MaxCount=1,
                SecurityGroupIds=[settings.AWS_SECURITY_GROUP_ID],
                KeyName=settings.AWS_KEY_PAIR_NAME,
                TagSpecifications=[
                    {
                        "ResourceType": "instance",
                        "Tags": [
                            {"Key": "Name", "Value": f"GPUScheduler-{new_gpu.id}"},
                            {"Key": "OrganizationID", "Value": str(new_gpu.organization_id)},
                            {"Key": "UserID", "Value": str(new_gpu.user_id)},
                        ],
                    }
                ],
            )[0]

            print(f"Requested EC2 instance with ID: {instance.id}")
            instance.wait_until_running()
            instance.reload()
            print(f"EC2 instance {instance.id} is running.")

            new_gpu.status = GpuStatus.AVAILABLE
            new_gpu.instance_id = instance.id
            new_gpu.instance_public_ip = instance.public_ip_address
            await db.commit()
            print(f"GPU {new_gpu.id} is now available.")

            return {"status": "complete", "gpu_id": str(new_gpu.id), "instance_id": instance.id}

        except Exception as e:
            print(f"Error provisioning GPU: {e}")
            new_gpu.status = GpuStatus.ERROR
            await db.commit()
            return {"status": "error", "error_message": str(e)}

        finally:
            await db.close()

    return asyncio.run(_provision())


@celery_app.task(bind=True)
def deprovision_gpu(self, gpu_id: str):
    """
    A Celery task to de-provision a GPU on AWS.
    """
    async def _deprovision():
        print(f"Received GPU de-provisioning task for GPU ID: {gpu_id}")
        db: AsyncSession = AsyncSessionLocal()
        
        try:
            gpu = await db.get(GPU, gpu_id)
            if not gpu:
                print(f"GPU with ID {gpu_id} not found.")
                return {"status": "not_found"}

            if gpu.instance_id:
                ec2 = boto3.resource("ec2", region_name=settings.AWS_REGION)
                instance = ec2.Instance(gpu.instance_id)
                instance.terminate()
                print(f"Terminated EC2 instance {gpu.instance_id}")

            gpu.status = GpuStatus.DEPROVISIONED
            await db.commit()
            print(f"GPU {gpu.id} has been de-provisioned.")

            return {"status": "complete", "gpu_id": str(gpu.id)}

        except Exception as e:
            print(f"Error de-provisioning GPU: {e}")
            # Optionally, set status to ERROR or another state
            return {"status": "error", "error_message": str(e)}

        finally:
            await db.close()

    return asyncio.run(_deprovision())